"""Milestone progress and forecast: when it will be done at the recent pace."""

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import Milestone, Status, StatusCategory, Ticket, User
from radicle.services import search

WEEKS = 4

ForecastState = Literal["on_track", "at_risk", "no_forecast", "done"]


@dataclass(frozen=True)
class Progress:
    milestone: str
    target_date: date | None
    tickets: int
    done: int
    percent_by_count: float
    hours_total: float
    hours_done: float
    percent_by_hours: float
    remaining_hours: float
    throughput_hours_per_week: float
    forecast_date: date | None
    state: ForecastState
    reason: str


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _remaining(t: Ticket) -> Decimal:
    if t.remaining_hours is not None:
        return t.remaining_hours
    return t.estimate_hours or Decimal(0)


async def milestone_progress(
    db: AsyncSession, user: User, milestone: Milestone, *, today: date
) -> Progress:
    """% done by count and by hours, and a forecast: today + remaining hours divided by the
    throughput (estimate hours finished per week, average of the last 4 weeks).

    Only tickets the user can see count. With no throughput there is no forecast."""
    rows = (
        await db.execute(
            search.base_query(user, include_restricted=True)
            .with_only_columns(Ticket, Status.category)
            .where(Ticket.milestone_id == milestone.id)
        )
    ).all()
    tickets = [(t, c) for t, c in rows]
    done = [t for t, c in tickets if c is StatusCategory.done]
    open_ = [t for t, c in tickets if c is not StatusCategory.done]
    hours_total = float(sum((t.estimate_hours or Decimal(0)) for t, _ in tickets))
    hours_done = float(sum((t.estimate_hours or Decimal(0)) for t in done))
    remaining = float(sum(_remaining(t) for t in open_))

    since = datetime.combine(today - timedelta(weeks=WEEKS), time(), UTC)
    recent = [t for t in done if t.resolved_at is not None and t.resolved_at >= since]
    throughput = float(sum((t.estimate_hours or Decimal(0)) for t in recent)) / WEEKS

    forecast: date | None = None
    state: ForecastState
    if tickets and not open_:
        state, reason = "done", "Every ticket is done."
    elif remaining == 0:
        state, reason = (
            "no_forecast",
            "Open tickets have no estimate, so there is nothing to divide by the pace.",
        )
    elif throughput == 0:
        state, reason = (
            "no_forecast",
            f"No estimated work was finished in the last {WEEKS} weeks, so there is no pace yet.",
        )
    else:
        forecast = today + timedelta(days=math.ceil(remaining / throughput * 7))
        target = milestone.target_date
        late = target is not None and forecast > target
        state = "at_risk" if late else "on_track"
        reason = f"{remaining:g} h left at {throughput:g} h/week finishes on {forecast.isoformat()}"
        reason += f", after the target {target.isoformat()}." if target and late else "."
    return Progress(
        milestone=milestone.name,
        target_date=milestone.target_date,
        tickets=len(tickets),
        done=len(done),
        percent_by_count=_pct(len(done), len(tickets)),
        hours_total=hours_total,
        hours_done=hours_done,
        percent_by_hours=_pct(hours_done, hours_total),
        remaining_hours=remaining,
        throughput_hours_per_week=round(throughput, 2),
        forecast_date=forecast,
        state=state,
        reason=reason,
    )


async def project_milestones(db: AsyncSession, project_id: object) -> list[Milestone]:
    rows = await db.scalars(
        select(Milestone)
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.position, Milestone.name)
    )
    return list(rows)
