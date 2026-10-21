"""Status periods (kept on every status change) and daily status snapshots."""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import case, delete, func, insert, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    DailyStatusCount,
    Project,
    SprintTicket,
    Status,
    StatusCategory,
    Ticket,
    TicketEvent,
    TicketStatusPeriod,
    utcnow,
)
from radicle.docket.services import period_builder
from radicle.platform.config import get_settings
from radicle.platform.services import queue

ZERO = uuid.UUID(int=0)
SNAPSHOT_JOB = "daily_snapshot"


async def track(db: AsyncSession, ticket: Ticket, event: TicketEvent) -> None:
    """Close the open period and open one for the ticket's current status, at the
    moment of `event`. Call it in the same transaction as the status change."""
    at = event.created_at
    open_period = await db.scalar(
        select(TicketStatusPeriod).where(
            TicketStatusPeriod.ticket_id == ticket.id, TicketStatusPeriod.exited_at.is_(None)
        )
    )
    if open_period is not None:
        if open_period.status_id == ticket.status_id:
            return
        open_period.exited_at = at
    category = await db.scalar(select(Status.category).where(Status.id == ticket.status_id))
    db.add(
        TicketStatusPeriod(
            ticket_id=ticket.id,
            status_id=ticket.status_id,
            category=category or StatusCategory.todo,
            entered_at=at,
        )
    )


async def backfill(db: AsyncSession, ticket_ids: list[uuid.UUID] | None = None) -> int:
    """Rebuild periods from `ticket_events` (all tickets, or the given ones)."""
    rows = await db.execute(
        select(Status.id, Status.ticket_type, Status.name, Status.category, Project.key).join(
            Project, Project.id == Status.project_id
        )
    )
    by_name: dict[tuple[str, str, str], tuple[Any, str]] = {}
    for status_id, ticket_type, name, category, key in rows.all():
        by_name[(key.upper(), ticket_type.value, name.lower())] = (status_id, category.value)

    def resolve(project_key: str | None, ticket_type: str, name: str) -> tuple[Any, str]:
        found = by_name.get(((project_key or "").upper(), ticket_type, name.lower()))
        return found if found else (None, StatusCategory.todo.value)

    query = select(Ticket.id, Ticket.type, Project.key).join(
        Project, Project.id == Ticket.project_id
    )
    if ticket_ids is not None:
        query = query.where(Ticket.id.in_(ticket_ids))
    tickets = (await db.execute(query)).all()
    ids = [t.id for t in tickets]
    await db.execute(delete(TicketStatusPeriod).where(TicketStatusPeriod.ticket_id.in_(ids)))
    events = await db.execute(
        select(
            TicketEvent.ticket_id,
            TicketEvent.event_type,
            TicketEvent.old_value,
            TicketEvent.new_value,
            TicketEvent.created_at,
        )
        .where(TicketEvent.ticket_id.in_(ids))
        .order_by(TicketEvent.ticket_id, TicketEvent.id)
    )
    grouped: dict[uuid.UUID, list[period_builder.Event]] = {}
    for ticket_id, event_type, old, new, at in events.all():
        grouped.setdefault(ticket_id, []).append(period_builder.Event(event_type, old, new, at))
    total = 0
    for ticket_id, ticket_type, key in tickets:
        built = period_builder.build(
            grouped.get(ticket_id, []),
            ticket_type=ticket_type.value,
            project_key=key,
            resolve=resolve,
        )
        for p in built:
            db.add(
                TicketStatusPeriod(
                    ticket_id=ticket_id,
                    status_id=p.status_id,
                    category=StatusCategory(p.category),
                    entered_at=p.entered_at,
                    exited_at=p.exited_at,
                )
            )
        total += len(built)
    await db.flush()
    return total


# --- daily snapshots -----------------------------------------------------------------------


def day_end(day: date, tz: str | None = None) -> datetime:
    """The first instant after `day` in the instance time zone, in UTC."""
    zone = ZoneInfo(tz or get_settings().timezone)
    return datetime.combine(day + timedelta(days=1), time(), zone).astimezone(UTC)


def today(tz: str | None = None) -> date:
    return utcnow().astimezone(ZoneInfo(tz or get_settings().timezone)).date()


def _sprint_key(end: datetime) -> Any:
    """Sprint the ticket was in at `end`; the zero uuid when none."""
    sprint = (
        select(SprintTicket.sprint_id)
        .where(
            SprintTicket.ticket_id == Ticket.id,
            SprintTicket.added_at < end,
            or_(SprintTicket.removed_at.is_(None), SprintTicket.removed_at >= end),
        )
        .order_by(SprintTicket.added_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    return func.coalesce(sprint, literal(ZERO))


async def snapshot(db: AsyncSession, day: date) -> int:
    """Replace the counts of `day`: tickets per status at the end of that day, by
    milestone and sprint. Running it twice gives the same rows."""
    end = day_end(day)
    await db.execute(delete(DailyStatusCount).where(DailyStatusCount.date == day))
    period = TicketStatusPeriod
    remaining = func.coalesce(Ticket.remaining_hours, Ticket.estimate_hours, literal(Decimal(0)))
    open_remaining = case((period.category != StatusCategory.done, remaining), else_=Decimal(0))
    milestone_key = func.coalesce(Ticket.milestone_id, literal(ZERO))
    sprint_key = _sprint_key(end)
    rows = (
        select(
            literal(day).label("date"),
            Ticket.project_id,
            period.status_id,
            milestone_key.label("milestone_key"),
            sprint_key.label("sprint_key"),
            func.count().label("ticket_count"),
            func.sum(open_remaining).label("remaining_hours"),
        )
        .select_from(period)
        .join(Ticket, Ticket.id == period.ticket_id)
        .where(
            period.status_id.is_not(None),
            period.entered_at < end,
            or_(period.exited_at.is_(None), period.exited_at >= end),
            or_(Ticket.deleted_at.is_(None), Ticket.deleted_at >= end),
        )
        .group_by(Ticket.project_id, period.status_id, milestone_key, sprint_key)
    )
    await db.execute(
        insert(DailyStatusCount).from_select(
            [
                "date",
                "project_id",
                "status_id",
                "milestone_key",
                "sprint_key",
                "ticket_count",
                "remaining_hours",
            ],
            rows,
        )
    )
    await db.flush()
    count = await db.scalar(
        select(func.count()).select_from(DailyStatusCount).where(DailyStatusCount.date == day)
    )
    return int(count or 0)


async def backfill_snapshots(db: AsyncSession, start: date, end: date | None = None) -> int:
    day, last, total = start, end or today(), 0
    while day <= last:
        total += await snapshot(db, day)
        day += timedelta(days=1)
    return total


@queue.handler(SNAPSHOT_JOB)
async def daily_snapshot(db: AsyncSession, **_: Any) -> None:
    """Hourly: yesterday (final) and today (so far). Idempotent."""
    now = today()
    await snapshot(db, now - timedelta(days=1))
    await snapshot(db, now)
