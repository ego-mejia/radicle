"""Batch-load everything a ticket response shows, for one ticket or a page of them."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.api.schemas.tickets import (
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
from radicle.db.models import (
    Area,
    Milestone,
    Project,
    Status,
    Ticket,
    TicketEvent,
    User,
)
from radicle.services import markdown, relations
from radicle.services.tickets import list_collaborators


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


async def ticket_out(
    db: AsyncSession, ticket: Ticket, *, warnings: list[WarningOut] | None = None
) -> TicketOut:
    await db.refresh(ticket, ["status", "assignee", "reporter"])
    ctx = await load_context(db, [ticket])
    collaborators = (await list_collaborators(db, [ticket.id])).get(ticket.id, [])
    children = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.parent_id == ticket.id, Ticket.deleted_at.is_(None))
    )
    links = await relations.links_for(db, ticket)
    parent = ctx.parents.get(ticket.parent_id) if ticket.parent_id else None
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
        parent=ctx.ref(parent) if parent else None,
        assignee=user_ref(ticket.assignee) if ticket.assignee else None,
        collaborators=[user_ref(u) for u in collaborators],
        reporter=user_ref(ticket.reporter),
        due_date=ticket.due_date,
        estimate_hours=_estimate(ticket),
        tags=list(ticket.tags),
        checklist=_checklist(ticket, ctx),
        links=[
            LinkOut(id=str(link.id), type=link.type, label=link.label, ticket=ctx_ref(link.other))
            for link in links
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
        warnings=warnings or [],
    )


def ctx_ref(other: relations.LinkedTicket) -> TicketRef:
    return TicketRef(
        key=other.key,
        title=other.title,
        type=other.type,
        status=StatusRef(name=other.status_name, category=other.category),
    )


async def summaries_out(db: AsyncSession, tickets: list[Ticket]) -> list[TicketSummary]:
    ctx = await load_context(db, tickets)
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
                blocked=bool(ctx.blocked_by.get(t.id)),
                due_date=t.due_date,
                estimate_hours=_estimate(t),
                checklist_done=sum(i.checked for i in items),
                checklist_total=len(items),
                rank=t.rank,
                updated_at=t.updated_at,
            )
        )
    return result


def event_out(event: TicketEvent) -> EventOut:
    return EventOut(
        id=event.id,
        event_type=event.event_type,
        field=event.field,
        old_value=event.old_value,
        new_value=event.new_value,
        actor=user_ref(event.actor),
        created_at=event.created_at,
    )
