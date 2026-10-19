"""Votes and time tracking: worklogs, original estimate and remaining time.

- The first estimate a ticket gets is copied to `original_estimate_hours` for good.
- Remaining time in `auto` mode is max(estimate - spent, 0); editing it by hand switches
  the ticket to `manual` until someone sets it back to `auto`.
- `time_spent_minutes` and `vote_count` are kept in the same transaction as the rows
  they summarize.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Forbidden, NotFound, ValidationFailed
from radicle.db.models import (
    EventType,
    Project,
    Ticket,
    TicketVote,
    User,
    UserKind,
    Worklog,
    utcnow,
)
from radicle.services import history
from radicle.services.access import ProjectAccess, access_for
from radicle.services.remaining import recompute_remaining
from radicle.services.ticket_fields import estimate_json
from radicle.services.tickets import bump

MINUTES_MAX = 1440
DESCRIPTION_MAX = 2000


# --- votes ---------------------------------------------------------------------------------


async def set_vote(db: AsyncSession, access: ProjectAccess, ticket: Ticket, voted: bool) -> bool:
    """Add or remove the caller's vote. Returns whether anything changed. Agents don't vote."""
    if access.user.kind is not UserKind.human:
        raise Forbidden("Only people vote; agents can read vote_count.", code="agents_do_not_vote")
    if voted:
        inserted = await db.execute(
            pg_insert(TicketVote)
            .values(ticket_id=ticket.id, user_id=access.user.id)
            .on_conflict_do_nothing()
            .returning(TicketVote.user_id)
        )
        changed = inserted.first() is not None
        delta = 1
    else:
        removed = await db.execute(
            delete(TicketVote)
            .where(TicketVote.ticket_id == ticket.id, TicketVote.user_id == access.user.id)
            .returning(TicketVote.user_id)
        )
        changed = removed.first() is not None
        delta = -1
    if not changed:
        return False
    count = await db.scalar(
        update(Ticket)
        .where(Ticket.id == ticket.id)
        .values(vote_count=Ticket.vote_count + delta)
        .returning(Ticket.vote_count)
    )
    ticket.vote_count = int(count or 0)
    history.record(
        db, ticket, access.user, EventType.vote_added if voted else EventType.vote_removed
    )
    await db.flush()
    return True


async def voters(db: AsyncSession, ticket_id: uuid.UUID) -> list[User]:
    rows = await db.scalars(
        select(TicketVote).where(TicketVote.ticket_id == ticket_id).order_by(TicketVote.created_at)
    )
    return [v.user for v in rows]


async def voted_by(
    db: AsyncSession, ticket_ids: list[uuid.UUID], user_id: uuid.UUID
) -> set[uuid.UUID]:
    if not ticket_ids:
        return set()
    rows = await db.scalars(
        select(TicketVote.ticket_id).where(
            TicketVote.ticket_id.in_(ticket_ids), TicketVote.user_id == user_id
        )
    )
    return set(rows)


# --- worklogs ------------------------------------------------------------------------------


@dataclass(frozen=True)
class WorklogAccess:
    access: ProjectAccess
    ticket: Ticket
    worklog: Worklog


def _minutes(value: int) -> int:
    if not 1 <= value <= MINUTES_MAX:
        raise ValidationFailed(
            f"Minutes must be between 1 and {MINUTES_MAX} (24 hours) per worklog.",
            errors=[{"field": "minutes", "message": "out of range"}],
        )
    return value


def _description(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if len(text) > DESCRIPTION_MAX:
        raise ValidationFailed(
            f"Description must be at most {DESCRIPTION_MAX} characters.",
            errors=[{"field": "description", "message": "too long"}],
        )
    return text or None


async def _apply_spent(db: AsyncSession, ticket: Ticket, delta: int, actor: User) -> None:
    """Add to the time spent; a remaining change it causes goes to the history too, so
    burndowns can tell the remaining hours of any past day."""
    before = ticket.remaining_hours
    total = await db.scalar(
        update(Ticket)
        .where(Ticket.id == ticket.id)
        .values(time_spent_minutes=Ticket.time_spent_minutes + delta)
        .returning(Ticket.time_spent_minutes)
    )
    ticket.time_spent_minutes = int(total or 0)
    recompute_remaining(ticket)
    if ticket.remaining_hours != before:
        history.record(
            db,
            ticket,
            actor,
            EventType.field_changed,
            field="remaining_hours",
            old=estimate_json(before),
            new=estimate_json(ticket.remaining_hours),
        )


def _log_json(worklog: Worklog) -> dict[str, object]:
    return {
        "id": str(worklog.id),
        "minutes": worklog.minutes,
        "started_at": worklog.started_at.isoformat(),
        "description": worklog.description,
    }


async def add_worklog(
    db: AsyncSession,
    access: ProjectAccess,
    ticket: Ticket,
    *,
    minutes: int,
    started_at: datetime | None = None,
    description: str | None = None,
) -> Worklog:
    worklog = Worklog(
        id=uuid.uuid4(),
        ticket_id=ticket.id,
        user_id=access.user.id,
        minutes=_minutes(minutes),
        started_at=started_at or utcnow(),
        description=_description(description),
    )
    db.add(worklog)
    await db.flush()
    await _apply_spent(db, ticket, worklog.minutes, access.user)
    history.record(
        db, ticket, access.user, EventType.worklog_added, field="worklog", new=_log_json(worklog)
    )
    bump(ticket)
    await db.flush()
    await db.refresh(worklog, ["user"])
    return worklog


async def list_worklogs(db: AsyncSession, ticket: Ticket) -> list[Worklog]:
    return list(
        await db.scalars(
            select(Worklog)
            .where(Worklog.ticket_id == ticket.id, Worklog.deleted_at.is_(None))
            .order_by(Worklog.started_at.desc(), Worklog.id)
        )
    )


async def load_worklog(db: AsyncSession, user: User, worklog_id: uuid.UUID) -> WorklogAccess:
    """Only the author or a project admin can change a worklog."""
    not_found = NotFound(f"Worklog {worklog_id} not found.", code="worklog_not_found")
    worklog = await db.scalar(
        select(Worklog).where(Worklog.id == worklog_id).with_for_update(of=Worklog)
    )
    if worklog is None or worklog.deleted_at is not None:
        raise not_found
    ticket = await db.scalar(
        select(Ticket).where(Ticket.id == worklog.ticket_id).with_for_update(of=Ticket)
    )
    project = await db.get(Project, ticket.project_id) if ticket else None
    if ticket is None or project is None or ticket.deleted_at is not None:
        raise not_found
    try:
        access = await access_for(db, user, project, write=True)
    except NotFound:
        raise not_found from None
    access.require("worklog.create" if worklog.user_id == user.id else "worklog.edit_any")
    return WorklogAccess(access, ticket, worklog)


async def update_worklog(
    db: AsyncSession,
    wa: WorklogAccess,
    *,
    minutes: int | None = None,
    started_at: datetime | None = None,
    description: str | None = None,
    clear_description: bool = False,
) -> Worklog:
    worklog = wa.worklog
    old = _log_json(worklog)
    if minutes is not None:
        delta = _minutes(minutes) - worklog.minutes
        worklog.minutes = minutes
        if delta:
            await _apply_spent(db, wa.ticket, delta, wa.access.user)
    if started_at is not None:
        worklog.started_at = started_at
    if clear_description:
        worklog.description = None
    elif description is not None:
        worklog.description = _description(description)
    worklog.updated_at = utcnow()
    history.record(
        db,
        wa.ticket,
        wa.access.user,
        EventType.worklog_updated,
        field="worklog",
        old=old,
        new=_log_json(worklog),
    )
    bump(wa.ticket)
    await db.flush()
    return worklog


async def delete_worklog(db: AsyncSession, wa: WorklogAccess) -> None:
    wa.worklog.deleted_at = utcnow()
    await _apply_spent(db, wa.ticket, -wa.worklog.minutes, wa.access.user)
    history.record(
        db,
        wa.ticket,
        wa.access.user,
        EventType.worklog_deleted,
        field="worklog",
        old=_log_json(wa.worklog),
    )
    bump(wa.ticket)
    await db.flush()
