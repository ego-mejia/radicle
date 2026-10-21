"""What other apps may ask of Docket (Folio 4.1). Folio reads and creates tickets only
through these functions, never Docket's tables, and always with the user's own access:
a ticket they can't see comes back as None, the same as one that does not exist."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.core import permissions
from radicle.docket.db.models import (
    Area,
    Milestone,
    Project,
    Ticket,
    TicketType,
    User,
)
from radicle.docket.services import search as docket_search
from radicle.docket.services import tickets as docket_tickets
from radicle.docket.services.access import project_access
from radicle.docket.services.ticket_fields import KEY_RE
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import markdown

MAX_KEYS = 100


@dataclass(frozen=True)
class TicketSummary:
    id: uuid.UUID
    key: str
    title: str
    type: str
    status: str
    status_category: str
    priority: str
    assignee_handle: str | None
    assignee_name: str | None
    area: str | None
    milestone: str | None
    checklist_done: int
    checklist_total: int


@dataclass(frozen=True)
class SearchResult:
    tickets: list[TicketSummary]
    total: int


@dataclass
class NewTicket:
    project: str
    title: str
    description_md: str = ""
    type: str = "task"
    area: str | None = None
    milestone: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MilestoneSummary:
    id: uuid.UUID
    project: str
    name: str
    status: str
    target_date: date | None


def parse_key(key: str) -> tuple[str, int] | None:
    match = KEY_RE.fullmatch(key.strip())
    return (match.group(1).upper(), int(match.group(2))) if match else None


async def _names(db: AsyncSession, id_col: Any, name_col: Any, ids: set[Any]) -> dict[Any, str]:
    if not ids:
        return {}
    return {i: n for i, n in (await db.execute(select(id_col, name_col).where(id_col.in_(ids))))}


async def _summaries(db: AsyncSession, tickets: list[Ticket]) -> list[TicketSummary]:
    keys = await _names(db, Project.id, Project.key, {t.project_id for t in tickets})
    areas = await _names(db, Area.id, Area.name, {t.area_id for t in tickets if t.area_id})
    milestones = await _names(
        db, Milestone.id, Milestone.name, {t.milestone_id for t in tickets if t.milestone_id}
    )
    out = []
    for t in tickets:
        items = markdown.parse_checklist(t.description_md)
        out.append(
            TicketSummary(
                id=t.id,
                key=f"{keys[t.project_id]}-{t.number}",
                title=t.title,
                type=t.type.value,
                status=t.status.name,
                status_category=t.status.category.value,
                priority=t.priority.value,
                assignee_handle=t.assignee.handle if t.assignee else None,
                assignee_name=t.assignee.display_name if t.assignee else None,
                area=areas.get(t.area_id) if t.area_id else None,
                milestone=milestones.get(t.milestone_id) if t.milestone_id else None,
                checklist_done=sum(1 for i in items if i.checked),
                checklist_total=len(items),
            )
        )
    return out


def _visible(user: User) -> Select[Any]:
    return select(Ticket).where(
        Ticket.deleted_at.is_(None), permissions.visible_tickets_clause(user)
    )


async def get_tickets(
    db: AsyncSession, keys: list[str], user: User
) -> dict[str, TicketSummary | None]:
    """Each asked key (upper-cased) with its ticket, or None if the user can't see it."""
    asked = {k.strip().upper(): parse_key(k) for k in keys[:MAX_KEYS]}
    pairs = [p for p in asked.values() if p is not None]
    found: dict[str, TicketSummary] = {}
    if pairs:
        rows = await db.scalars(
            _visible(user)
            .join(Project, Project.id == Ticket.project_id)
            .where(or_(*(and_(Project.key == p, Ticket.number == n) for p, n in pairs)))
        )
        found = {s.key: s for s in await _summaries(db, list(rows))}
    return {key: found.get(key) for key in asked}


async def get_tickets_by_id(
    db: AsyncSession, ids: list[uuid.UUID], user: User
) -> dict[uuid.UUID, TicketSummary]:
    """The tickets among `ids` the user can see; the others are missing from the result."""
    if not ids:
        return {}
    rows = await db.scalars(_visible(user).where(Ticket.id.in_(ids)))
    return {s.id: s for s in await _summaries(db, list(rows))}


async def search(db: AsyncSession, rql: str, user: User, *, limit: int = 50) -> SearchResult:
    """Docket's RQL search, limited to what the user sees. Bad RQL raises its usual error."""
    result = await docket_search.search(db, user, rql, limit=limit)
    return SearchResult(await _summaries(db, result.tickets), result.total)


async def create_ticket(db: AsyncSession, data: NewTicket, user: User) -> TicketSummary:
    """Create a ticket as the user, with Docket's own checks (ticket.create, area rules)."""
    if data.type not in {t.value for t in TicketType}:
        raise ValidationFailed(
            f"Unknown ticket type {data.type}. Use task, bug or draft.",
            errors=[{"field": "type", "message": "invalid"}],
        )
    access = await project_access(
        db, user, data.project.strip().upper(), write=True, permission="ticket.create"
    )
    ticket = await docket_tickets.create_ticket(
        db,
        access,
        docket_tickets.NewTicket(
            type=TicketType(data.type),
            title=data.title,
            description_md=data.description_md,
            area=data.area,
            milestone=data.milestone,
            tags=data.tags,
        ),
    )
    await db.refresh(ticket, ["status", "assignee"])
    return (await _summaries(db, [ticket]))[0]


async def get_milestone(
    db: AsyncSession, project: str, name: str, user: User
) -> MilestoneSummary | None:
    """A milestone of a project the user can see, by name (any case), or None."""
    try:
        access = await project_access(db, user, project.strip().upper())
    except NotFound:
        return None
    found = await db.scalar(
        select(Milestone).where(
            Milestone.project_id == access.project.id,
            func.lower(Milestone.name) == name.strip().lower(),
        )
    )
    if found is None:
        return None
    return MilestoneSummary(
        found.id, access.project.key, found.name, found.status.value, found.target_date
    )


async def get_area(db: AsyncSession, project: str, name: str, user: User) -> str | None:
    """An area's name as Docket spells it, in a project the user can see, or None."""
    try:
        access = await project_access(db, user, project.strip().upper())
    except NotFound:
        return None
    return await db.scalar(
        select(Area.name).where(
            Area.project_id == access.project.id,
            func.lower(Area.name) == name.strip().lower(),
        )
    )
