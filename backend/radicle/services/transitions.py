"""Moving tickets through their workflow and changing their type."""

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import ValidationFailed
from radicle.db.models import (
    Area,
    EventType,
    Resolution,
    StatusCategory,
    Ticket,
    TicketType,
    utcnow,
)
from radicle.services import history, relations, workflow_engine
from radicle.services import ticket_fields as fields
from radicle.services.access import ProjectAccess
from radicle.services.tickets import bump
from radicle.services.workflows import load_workflows


@dataclass(frozen=True)
class TicketWarning:
    code: str
    message: str
    by: list[str] = field(default_factory=list)


async def available_transitions(db: AsyncSession, ticket: Ticket) -> list[workflow_engine.Option]:
    workflows = await load_workflows(db, ticket.project_id)
    workflow = workflows[ticket.type]
    return workflow_engine.available(workflow, workflow.status_by_id(ticket.status_id))


async def transition_ticket(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    to_status: str,
    resolution: Resolution | None = None,
    transition: str | None = None,
) -> list[TicketWarning]:
    workflows = await load_workflows(db, ticket.project_id)
    workflow = workflows[ticket.type]
    current = workflow.status_by_id(ticket.status_id)
    decision = workflow_engine.decide(workflow, current, to_status, resolution, transition)
    target = decision.option.to_status

    warnings: list[TicketWarning] = []
    if target.category in (StatusCategory.in_progress, StatusCategory.done):
        blockers = (await relations.blocked_by(db, [ticket.id])).get(ticket.id, [])
        if blockers:
            warnings.append(
                TicketWarning(
                    code="blocked",
                    message=f"Moved while blocked by {', '.join(blockers)}, which are not done.",
                    by=blockers,
                )
            )

    old = {"status": current.name, "resolution": _value(ticket.resolution)}
    ticket.status_id = target.id
    ticket.status = target
    if target.category is StatusCategory.done:
        ticket.resolution = decision.resolution
        if current.category is not StatusCategory.done or ticket.resolved_at is None:
            ticket.resolved_at = utcnow()
    else:
        ticket.resolution = None
        ticket.resolved_at = None
    history.record(
        db,
        ticket,
        access.user,
        EventType.status_changed,
        field="status",
        old=old,
        new={
            "status": target.name,
            "resolution": _value(ticket.resolution),
            "transition": decision.option.transition.name,
        },
    )
    bump(ticket)
    await db.flush()
    return warnings


async def change_type(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    new_type: TicketType,
    area: str | None = None,
) -> None:
    """Switch type: the ticket restarts at the new workflow's initial status."""
    if new_type is ticket.type:
        raise ValidationFailed(
            f"The ticket is already a {new_type.value}.",
            errors=[{"field": "type", "message": "unchanged"}],
        )
    project = access.project
    new_area = await fields.resolve_area(db, project, area) if area is not None else None
    if new_area is None and ticket.area_id is None:
        fields.require_area(new_type, None)

    workflows = await load_workflows(db, project.id)
    old_status = workflows[ticket.type].status_by_id(ticket.status_id)
    new_status = workflows[new_type].initial
    history.record(
        db,
        ticket,
        access.user,
        EventType.type_changed,
        field="type",
        old=ticket.type.value,
        new=new_type.value,
    )
    history.record(
        db,
        ticket,
        access.user,
        EventType.status_changed,
        field="status",
        old={"status": old_status.name, "resolution": _value(ticket.resolution)},
        new={"status": new_status.name, "resolution": None},
    )
    if new_area is not None and new_area.id != ticket.area_id:
        old_area = await db.get(Area, ticket.area_id) if ticket.area_id else None
        history.record(
            db,
            ticket,
            access.user,
            EventType.field_changed,
            field="area",
            old=old_area.name if old_area else None,
            new=new_area.name,
        )
        ticket.area_id = new_area.id
    ticket.type = new_type
    ticket.status_id = new_status.id
    ticket.status = new_status
    ticket.resolution = None
    ticket.resolved_at = None
    bump(ticket)
    await db.flush()


def _value(resolution: Resolution | None) -> str | None:
    return resolution.value if resolution is not None else None
