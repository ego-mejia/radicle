"""Batch-load everything a ticket response shows, for one ticket or a page of them."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.api.schemas.tickets import (
    AttachmentOut,
    ChecklistItemOut,
    EventOut,
    LinkOut,
    StatusRef,
    TicketOut,
    TicketRef,
    TicketSummary,
    UserRef,
    WarningOut,
)
from radicle.docket.core.permissions import can_see, visible_tickets_clause
from radicle.docket.db.models import (
    Area,
    Attachment,
    CustomFieldDefinition,
    Milestone,
    Project,
    SecurityLevel,
    Status,
    Ticket,
    TicketEvent,
    User,
)
from radicle.docket.services import attachments, custom_fields, relations, timetracking
from radicle.docket.services.remaining import spent_hours
from radicle.docket.services.tickets import list_collaborators
from radicle.platform.services import images, markdown


def user_ref(user: User) -> UserRef:
    return UserRef(handle=user.handle, display_name=user.display_name, kind=user.kind)


def status_ref(status: Status) -> StatusRef:
    return StatusRef(name=status.name, category=status.category)


@dataclass
class TicketContext:
    project_keys: dict[uuid.UUID, str] = field(default_factory=dict)
    areas: dict[uuid.UUID, str] = field(default_factory=dict)
    milestones: dict[uuid.UUID, str] = field(default_factory=dict)
    parents: dict[uuid.UUID, Ticket] = field(default_factory=dict)
    known_handles: set[str] = field(default_factory=set)
    blocked_by: dict[uuid.UUID, list[str]] = field(default_factory=dict)
    fields: dict[uuid.UUID, list[CustomFieldDefinition]] = field(default_factory=dict)
    user_handles: dict[str, str] = field(default_factory=dict)

    def custom_fields(self, ticket: Ticket) -> dict[str, object]:
        return custom_fields.visible_values(
            self.fields.get(ticket.project_id, []),
            ticket.custom_fields or {},
            ticket.type,
            ticket.area_id,
            self.user_handles,
        )

    def key(self, ticket: Ticket) -> str:
        return f"{self.project_keys[ticket.project_id]}-{ticket.number}"

    def ref(self, ticket: Ticket) -> TicketRef:
        return TicketRef(
            key=self.key(ticket),
            title=ticket.title,
            type=ticket.type,
            status=status_ref(ticket.status),
        )


async def load_context(db: AsyncSession, tickets: list[Ticket]) -> TicketContext:
    ctx = TicketContext()
    if not tickets:
        return ctx
    project_ids = {t.project_id for t in tickets}
    rows = await db.execute(select(Project.id, Project.key).where(Project.id.in_(project_ids)))
    ctx.project_keys = {pid: key for pid, key in rows.all()}
    area_ids = {t.area_id for t in tickets if t.area_id}
    if area_ids:
        rows = await db.execute(select(Area.id, Area.name).where(Area.id.in_(area_ids)))
        ctx.areas = {aid: name for aid, name in rows.all()}
    milestone_ids = {t.milestone_id for t in tickets if t.milestone_id}
    if milestone_ids:
        rows = await db.execute(
            select(Milestone.id, Milestone.name).where(Milestone.id.in_(milestone_ids))
        )
        ctx.milestones = {mid: name for mid, name in rows.all()}
    parent_ids = {t.parent_id for t in tickets if t.parent_id}
    if parent_ids:
        parents = await db.scalars(select(Ticket).where(Ticket.id.in_(parent_ids)))
        ctx.parents = {p.id: p for p in parents}
    handles = {
        item.assignee
        for t in tickets
        for item in markdown.parse_checklist(t.description_md)
        if item.assignee
    }
    if handles:
        ctx.known_handles = set(
            await db.scalars(select(User.handle).where(User.handle.in_(handles)))
        )
    ctx.blocked_by = await relations.blocked_by(db, [t.id for t in tickets])
    if any(t.custom_fields for t in tickets):
        definitions = await db.scalars(
            select(CustomFieldDefinition)
            .where(
                CustomFieldDefinition.project_id.in_(project_ids),
                CustomFieldDefinition.archived_at.is_(None),
            )
            .order_by(CustomFieldDefinition.position)
        )
        user_fields: set[str] = set()
        for d in definitions:
            ctx.fields.setdefault(d.project_id, []).append(d)
            if d.field_type.value == "user":
                user_fields.add(d.key)
        ids = [t.custom_fields[k] for t in tickets for k in user_fields if k in t.custom_fields]
        ctx.user_handles = await custom_fields.user_handles(db, ids)
    return ctx


def _checklist(ticket: Ticket, ctx: TicketContext) -> list[ChecklistItemOut]:
    return [
        ChecklistItemOut(
            index=item.index,
            text=item.text,
            checked=item.checked,
            assignee=item.assignee,
            assignee_unknown=item.assignee is not None and item.assignee not in ctx.known_handles,
        )
        for item in markdown.parse_checklist(ticket.description_md)
    ]


def _estimate(ticket: Ticket) -> float | None:
    return float(ticket.estimate_hours) if ticket.estimate_hours is not None else None


def _hours(value: object) -> float | None:
    return float(value) if value is not None else None  # type: ignore[arg-type]


async def ticket_out(
    db: AsyncSession,
    ticket: Ticket,
    *,
    warnings: list[WarningOut] | None = None,
    viewer: User | None = None,
) -> TicketOut:
    await db.refresh(ticket, ["status", "assignee", "reporter"])
    ctx = await load_context(db, [ticket])
    collaborators = (await list_collaborators(db, [ticket.id])).get(ticket.id, [])
    children = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.parent_id == ticket.id,
            Ticket.deleted_at.is_(None),
            visible_tickets_clause(viewer) if viewer is not None else true(),
        )
    )
    links = await relations.links_for(db, ticket, viewer)
    parent = ctx.parents.get(ticket.parent_id) if ticket.parent_id else None
    parent_ref = ctx.ref(parent) if parent else None
    if parent is not None and viewer is not None and not await can_see(db, viewer, parent):
        parent_ref = RESTRICTED_REF
    return TicketOut(
        key=ctx.key(ticket),
        project=ctx.project_keys[ticket.project_id],
        type=ticket.type,
        title=ticket.title,
        description_md=ticket.description_md,
        status=status_ref(ticket.status),
        resolution=ticket.resolution,
        priority=ticket.priority,
        area=ctx.areas.get(ticket.area_id) if ticket.area_id else None,
        milestone=ctx.milestones.get(ticket.milestone_id) if ticket.milestone_id else None,
        parent=parent_ref,
        assignee=user_ref(ticket.assignee) if ticket.assignee else None,
        collaborators=[user_ref(u) for u in collaborators],
        reporter=user_ref(ticket.reporter),
        start_date=ticket.start_date,
        due_date=ticket.due_date,
        estimate_hours=_estimate(ticket),
        original_estimate_hours=_hours(ticket.original_estimate_hours),
        remaining_hours=_hours(ticket.remaining_hours),
        remaining_mode=ticket.remaining_mode,
        spent_hours=float(spent_hours(ticket)),
        vote_count=ticket.vote_count,
        voted_by_me=viewer is not None
        and bool(await timetracking.voted_by(db, [ticket.id], viewer.id)),
        tags=list(ticket.tags),
        custom_fields=ctx.custom_fields(ticket),
        checklist=_checklist(ticket, ctx),
        links=[
            LinkOut(id=str(link.id), type=link.type, label=link.label, ticket=ctx_ref(link.other))
            for link in links
        ],
        attachments=[
            attachment_out(a, ctx.key(ticket))
            for a in await attachments.list_attachments(db, [ticket.id])
        ],
        children_count=int(children or 0),
        comments_count=await relations.comments_count(db, ticket.id),
        blocked=bool(ctx.blocked_by.get(ticket.id)),
        rank=ticket.rank,
        version=ticket.version,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        deleted=ticket.deleted_at is not None,
        security_level=await _level_name(db, ticket),
        origin=ticket.origin,
        classification=ticket.classification,
        impact=ticket.impact,
        effort=ticket.effort,
        converted_at=ticket.converted_at,
        submitter_name=ticket.submitter_name,
        submitter_email=ticket.submitter_email,
        warnings=warnings or [],
    )


async def _level_name(db: AsyncSession, ticket: Ticket) -> str | None:
    if ticket.security_level_id is None:
        return None
    level = await db.get(SecurityLevel, ticket.security_level_id)
    return level.name if level else None


RESTRICTED_REF = TicketRef(key=None, title=None, type=None, status=None, restricted=True)


def ctx_ref(other: relations.LinkedTicket) -> TicketRef:
    if other.restricted:
        return RESTRICTED_REF
    return TicketRef(
        key=other.key,
        title=other.title,
        type=other.type,
        status=StatusRef(name=other.status_name, category=other.category),
    )


async def summaries_out(
    db: AsyncSession, tickets: list[Ticket], viewer: User | None = None
) -> list[TicketSummary]:
    """Rows for lists. With a `viewer`, each row also says its parent (if the viewer may
    see it) and how many subtickets the viewer may see, so lists can nest them."""
    ctx = await load_context(db, tickets)
    visible_parents: set[uuid.UUID] = set()
    child_counts: dict[uuid.UUID, int] = {}
    if viewer is not None and tickets:
        missing = {p.project_id for p in ctx.parents.values()} - set(ctx.project_keys)
        if missing:  # a parent can live in another project after a move
            rows = await db.execute(select(Project.id, Project.key).where(Project.id.in_(missing)))
            ctx.project_keys.update({pid: key for pid, key in rows.all()})
        if ctx.parents:
            visible_parents = set(
                await db.scalars(
                    select(Ticket.id).where(
                        Ticket.id.in_(ctx.parents), visible_tickets_clause(viewer)
                    )
                )
            )
        counts = await db.execute(
            select(Ticket.parent_id, func.count())
            .where(
                Ticket.parent_id.in_([t.id for t in tickets]),
                Ticket.deleted_at.is_(None),
                visible_tickets_clause(viewer),
            )
            .group_by(Ticket.parent_id)
        )
        child_counts = {pid: n for pid, n in counts.all() if pid is not None}
    result = []
    for t in tickets:
        items = markdown.parse_checklist(t.description_md)
        result.append(
            TicketSummary(
                key=ctx.key(t),
                title=t.title,
                type=t.type,
                status=status_ref(t.status),
                resolution=t.resolution,
                priority=t.priority,
                assignee=user_ref(t.assignee) if t.assignee else None,
                area=ctx.areas.get(t.area_id) if t.area_id else None,
                milestone=ctx.milestones.get(t.milestone_id) if t.milestone_id else None,
                tags=list(t.tags),
                custom_fields=ctx.custom_fields(t),
                blocked=bool(ctx.blocked_by.get(t.id)),
                start_date=t.start_date,
                due_date=t.due_date,
                estimate_hours=_estimate(t),
                spent_hours=float(spent_hours(t)),
                vote_count=t.vote_count,
                checklist_done=sum(i.checked for i in items),
                checklist_total=len(items),
                rank=t.rank,
                updated_at=t.updated_at,
                created_at=t.created_at,
                origin=t.origin,
                classification=t.classification,
                impact=t.impact,
                effort=t.effort,
                converted=t.converted_at is not None,
                parent=(
                    ctx.key(ctx.parents[t.parent_id]) if t.parent_id in visible_parents else None
                ),
                child_count=child_counts.get(t.id, 0) if viewer is not None else None,
            )
        )
    return result


def _url(attachment: Attachment, variant: str) -> str:
    query = attachments.signed_query(attachment.id, variant)
    return f"/api/v1/attachments/{attachment.id}/content?{query}"


def attachment_out(attachment: Attachment, key: str) -> AttachmentOut:
    image = images.is_image(attachment.mime_type)
    ready = image and bool(attachment.variants)
    target = f"attachment:{attachment.id}"
    return AttachmentOut(
        id=str(attachment.id),
        ticket=key,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=attachment.size_bytes,
        is_image=image,
        width=attachment.width,
        height=attachment.height,
        uploader=user_ref(attachment.uploader),
        comment_id=str(attachment.comment_id) if attachment.comment_id else None,
        created_at=attachment.created_at,
        url=_url(attachment, "original"),
        thumb_url=_url(attachment, "thumb") if ready else None,
        preview_url=_url(attachment, "preview") if ready else None,
        markdown=f"![{attachment.filename}]({target})"
        if image
        else f"[{attachment.filename}]({target})",
    )


def event_out(event: TicketEvent, values: tuple[Any, Any] | None = None) -> EventOut:
    old, new = values if values is not None else (event.old_value, event.new_value)
    return EventOut(
        id=event.id,
        event_type=event.event_type,
        field=event.field,
        old_value=old,
        new_value=new,
        actor=user_ref(event.actor),
        created_at=event.created_at,
    )
