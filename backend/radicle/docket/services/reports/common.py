"""Shared pieces for reports: the result shape, days, and replaying ticket state at a moment."""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    EventType,
    StatusCategory,
    Ticket,
    TicketEvent,
    TicketStatusPeriod,
)
from radicle.docket.services.periods import day_end
from radicle.platform.errors import ValidationFailed

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MAX_DAYS = 400


@dataclass
class Report:
    """Every report: rows for the table and CSV, plus a summary for people and agents."""

    type: str
    title: str
    columns: list[str]
    rows: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def fail(param: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": param, "message": "invalid"}])


def parse_workdays(text: str) -> set[int]:
    days = {WEEKDAYS.index(d.strip().lower()) for d in text.split(",") if d.strip() in WEEKDAYS}
    return days or {0, 1, 2, 3, 4}


def days_between(start: date, end: date) -> list[date]:
    if end < start:
        raise fail("to", "The end of the range is before its start.")
    count = (end - start).days + 1
    if count > MAX_DAYS:
        raise fail("from", f"The range is {count} days; reports cover up to {MAX_DAYS}.")
    return [start + timedelta(days=i) for i in range(count)]


def hours(value: Decimal | float | None) -> float:
    return round(float(value or 0), 2)


async def categories_at(
    db: AsyncSession, ticket_ids: list[uuid.UUID], moments: list[datetime]
) -> dict[uuid.UUID, list[StatusCategory | None]]:
    """Each ticket's status category at each moment (None before it existed)."""
    out: dict[uuid.UUID, list[StatusCategory | None]] = {
        t: [None] * len(moments) for t in ticket_ids
    }
    if not ticket_ids:
        return out
    rows = await db.execute(
        select(
            TicketStatusPeriod.ticket_id,
            TicketStatusPeriod.category,
            TicketStatusPeriod.entered_at,
            TicketStatusPeriod.exited_at,
        ).where(TicketStatusPeriod.ticket_id.in_(ticket_ids))
    )
    for ticket_id, category, entered, exited in rows:
        for i, moment in enumerate(moments):
            if entered < moment and (exited is None or exited >= moment):
                out[ticket_id][i] = category
    return out


async def remaining_at(
    db: AsyncSession, tickets: list[Ticket], moments: list[datetime]
) -> dict[uuid.UUID, list[Decimal]]:
    """Remaining hours of each ticket at each moment, replayed from `remaining_hours`
    changes in the history: the last value set before the moment, else the value the
    first later change replaced, else today's value."""
    events: dict[uuid.UUID, list[tuple[datetime, Any, Any]]] = defaultdict(list)
    if tickets:
        rows = await db.execute(
            select(
                TicketEvent.ticket_id,
                TicketEvent.created_at,
                TicketEvent.old_value,
                TicketEvent.new_value,
            )
            .where(
                TicketEvent.ticket_id.in_([t.id for t in tickets]),
                TicketEvent.event_type == EventType.field_changed.value,
                TicketEvent.field == "remaining_hours",
            )
            .order_by(TicketEvent.id)
        )
        for ticket_id, at, old, new in rows:
            events[ticket_id].append((at, old, new))
    out: dict[uuid.UUID, list[Decimal]] = {}
    for t in tickets:
        current = t.remaining_hours if t.remaining_hours is not None else t.estimate_hours
        values = []
        for moment in moments:
            before = [e for e in events[t.id] if e[0] <= moment]
            after = [e for e in events[t.id] if e[0] > moment]
            if before:
                value = before[-1][2]
            elif after:
                value = after[0][1]
            else:
                value = current
            values.append(Decimal(str(value)) if value is not None else Decimal(0))
        out[t.id] = values
    return out


def day_ends(days: list[date], tz: str) -> list[datetime]:
    return [day_end(d, tz) for d in days]


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile; None for no data."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * p // 100))
    return round(ordered[int(rank) - 1], 2)
