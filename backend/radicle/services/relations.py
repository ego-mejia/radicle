"""Links between tickets, the blocked state they imply, and comment counts."""

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from radicle.core.permissions import can_see, visible_tickets_clause
from radicle.db.models import (
    LINK_LABELS,
    Comment,
    EventType,
    LinkType,
    Project,
    Status,
    StatusCategory,
    Ticket,
    TicketLink,
    TicketType,
    User,
)
from radicle.platform.errors import Conflict, NotFound, ValidationFailed
from radicle.services import history
from radicle.services.access import ProjectAccess, access_for
from radicle.services.tickets import bump, load_ticket


@dataclass(frozen=True)
class LinkedTicket:
    key: str
    title: str
    type: TicketType
    status_name: str
    category: StatusCategory
    restricted: bool = False


@dataclass(frozen=True)
class LinkView:
    id: uuid.UUID
    type: str
    label: str
    other: LinkedTicket


def label_for(link_type: LinkType, *, outgoing: bool) -> str:
    source_label, target_label = LINK_LABELS[link_type]
    return source_label if outgoing else target_label


async def _key(db: AsyncSession, ticket: Ticket) -> str:
    project_key = await db.scalar(select(Project.key).where(Project.id == ticket.project_id))
    return f"{project_key}-{ticket.number}"


async def links_for(db: AsyncSession, ticket: Ticket, viewer: User | None = None) -> list[LinkView]:
    """Links of a ticket from its point of view, skipping deleted tickets. Linked tickets
    the viewer may not see come back with `restricted` and no key or title."""
    other = aliased(Ticket)
    rows = await db.execute(
        select(TicketLink, other, Project.key, Status)
        .join(
            other,
            or_(
                and_(TicketLink.source_id == ticket.id, other.id == TicketLink.target_id),
                and_(TicketLink.target_id == ticket.id, other.id == TicketLink.source_id),
            ),
        )
        .join(Project, Project.id == other.project_id)
        .join(Status, Status.id == other.status_id)
        .where(other.deleted_at.is_(None))
        .order_by(TicketLink.created_at)
    )
    found = rows.all()
    hidden: set[uuid.UUID] = set()
    if viewer is not None and found:
        ids = {linked.id for _, linked, _, _ in found}
        seen = set(
            await db.scalars(
                select(Ticket.id).where(Ticket.id.in_(ids), visible_tickets_clause(viewer))
            )
        )
        hidden = ids - seen
    views = []
    for link, linked, project_key, status in found:
        outgoing = link.source_id == ticket.id
        views.append(
            LinkView(
                id=link.id,
                type=link.type.value,
                label=label_for(link.type, outgoing=outgoing),
                other=(
                    LinkedTicket("", "", linked.type, "", status.category, restricted=True)
                    if linked.id in hidden
                    else LinkedTicket(
                        key=f"{project_key}-{linked.number}",
                        title=linked.title,
                        type=linked.type,
                        status_name=status.name,
                        category=status.category,
                    )
                ),
            )
        )
    return views


async def blocked_by(db: AsyncSession, ticket_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """For each ticket, keys of live tickets that block it and are not done."""
    if not ticket_ids:
        return {}
    blocker = aliased(Ticket)
    rows = await db.execute(
        select(TicketLink.target_id, Project.key, blocker.number)
        .join(blocker, blocker.id == TicketLink.source_id)
        .join(Project, Project.id == blocker.project_id)
        .join(Status, Status.id == blocker.status_id)
        .where(
            TicketLink.type == LinkType.blocks,
            TicketLink.target_id.in_(ticket_ids),
            blocker.deleted_at.is_(None),
            Status.category != StatusCategory.done,
        )
        .order_by(blocker.number)
    )
    result: dict[uuid.UUID, list[str]] = {}
    for target_id, project_key, number in rows.all():
        result.setdefault(target_id, []).append(f"{project_key}-{number}")
    return result


async def comments_count(db: AsyncSession, ticket_id: uuid.UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Comment)
        .where(Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None))
    )
    return int(count or 0)


async def _visible_target(db: AsyncSession, user: User, key: str) -> Ticket:
    try:
        _, target = await load_ticket(db, user, key)
    except NotFound as exc:
        raise ValidationFailed(
            f"Target ticket {key.strip().upper()} not found.",
            errors=[{"field": "target", "message": "not found"}],
        ) from exc
    return target


async def add_link(
    db: AsyncSession, access: ProjectAccess, source: Ticket, link_type: LinkType, target_key: str
) -> TicketLink:
    target = await _visible_target(db, access.user, target_key)
    if target.id == source.id:
        raise ValidationFailed(
            "A ticket cannot be linked to itself.",
            errors=[{"field": "target", "message": "same ticket"}],
        )
    existing = await db.scalar(
        select(TicketLink.id).where(
            TicketLink.type == link_type,
            or_(
                and_(TicketLink.source_id == source.id, TicketLink.target_id == target.id),
                and_(TicketLink.source_id == target.id, TicketLink.target_id == source.id),
            ),
        )
    )
    source_key, target_key_norm = await _key(db, source), await _key(db, target)
    if existing:
        raise Conflict(
            f"{source_key} and {target_key_norm} are already linked as {link_type.value}.",
            code="duplicate_link",
        )
    link = TicketLink(
        source_id=source.id, target_id=target.id, type=link_type, created_by=access.user.id
    )
    db.add(link)
    await db.flush()
    _record_link(db, access.user, source, target, link, source_key, target_key_norm, added=True)
    return link


async def remove_link(db: AsyncSession, user: User, link_id: uuid.UUID) -> None:
    link = await db.get(TicketLink, link_id)
    if link is None:
        raise NotFound(f"Link {link_id} not found.", code="link_not_found")
    source = await db.get(Ticket, link.source_id)
    target = await db.get(Ticket, link.target_id)
    if source is None or target is None:  # pragma: no cover - FK cascade
        raise NotFound(f"Link {link_id} not found.", code="link_not_found")
    project = await db.get(Project, source.project_id)
    if project is None:  # pragma: no cover - FK
        raise NotFound(f"Link {link_id} not found.", code="link_not_found")
    try:
        await access_for(db, user, project, write=True, permission="link.manage")
    except NotFound as exc:
        raise NotFound(f"Link {link_id} not found.", code="link_not_found") from exc
    if not await can_see(db, user, source) or not await can_see(db, user, target):
        raise NotFound(f"Link {link_id} not found.", code="link_not_found")
    source_key, target_key = await _key(db, source), await _key(db, target)
    _record_link(db, user, source, target, link, source_key, target_key, added=False)
    await db.delete(link)
    await db.flush()


def _record_link(
    db: AsyncSession,
    user: User,
    source: Ticket,
    target: Ticket,
    link: TicketLink,
    source_key: str,
    target_key: str,
    *,
    added: bool,
) -> None:
    event = EventType.link_added if added else EventType.link_removed
    for ticket, outgoing, other_key in ((source, True, target_key), (target, False, source_key)):
        value = {"label": label_for(link.type, outgoing=outgoing), "ticket": other_key}
        history.record(
            db,
            ticket,
            user,
            event,
            field="links",
            old=None if added else value,
            new=value if added else None,
        )
        bump(ticket)
