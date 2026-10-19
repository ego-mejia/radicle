"""General reports: created vs resolved, distribution by field, milestone progress, time."""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Area,
    CustomFieldDefinition,
    Milestone,
    Project,
    Status,
    Ticket,
    User,
)
from radicle.services import forecast, search
from radicle.services.remaining import spent_hours
from radicle.services.reports.common import Report, days_between, fail, hours

DISTRIBUTION_FIELDS = ("area", "priority", "assignee", "type", "status", "tag", "milestone")
TIME_GROUPS = ("ticket", "milestone", "area", "assignee")


def _bucket(day: date, interval: str) -> date:
    return day - timedelta(days=day.weekday()) if interval == "week" else day


async def created_vs_resolved(
    db: AsyncSession,
    user: User,
    *,
    ticket_filter: Any,
    start: date,
    end: date,
    interval: str,
    tz: str,
) -> Report:
    """Tickets created and resolved per day or week, and the running difference."""
    if interval not in ("day", "week"):
        raise fail("interval", "Use interval=day or interval=week.")
    zone = ZoneInfo(tz)
    days = days_between(start, end)
    buckets = sorted({_bucket(d, interval) for d in days})
    created: Counter[date] = Counter()
    resolved: Counter[date] = Counter()
    rows = await db.execute(
        search.base_query(user)
        .where(ticket_filter)
        .with_only_columns(Ticket.created_at, Ticket.resolved_at)
    )
    for created_at, resolved_at in rows:
        c = created_at.astimezone(zone).date()
        if start <= c <= end:
            created[_bucket(c, interval)] += 1
        if resolved_at is not None:
            r = resolved_at.astimezone(zone).date()
            if start <= r <= end:
                resolved[_bucket(r, interval)] += 1
    report = Report(
        "created_resolved",
        "Created vs resolved",
        ["period", "created", "resolved", "cumulative_difference"],
    )
    running = 0
    for b in buckets:
        running += created[b] - resolved[b]
        report.rows.append(
            {
                "period": b.isoformat(),
                "created": created[b],
                "resolved": resolved[b],
                "cumulative_difference": running,
            }
        )
    report.summary = {
        "created": sum(created.values()),
        "resolved": sum(resolved.values()),
        "difference": running,
        "interval": interval,
    }
    return report


async def distribution(db: AsyncSession, user: User, *, ticket_filter: Any, field: str) -> Report:
    """Ticket count per value of a field; custom select fields as cf.<key>."""
    custom = field[3:] if field.startswith("cf.") else None
    if custom is None and field not in DISTRIBUTION_FIELDS:
        raise fail(
            "field",
            f"Cannot group by '{field}'. Use {', '.join(DISTRIBUTION_FIELDS)} or cf.<key> "
            "of a select field.",
        )
    if custom is not None:
        exists = await db.scalar(
            select(CustomFieldDefinition.id).where(CustomFieldDefinition.key == custom).limit(1)
        )
        if exists is None:
            raise fail("field", f"There is no custom field '{custom}'.")
    tickets = list(await db.scalars(search.base_query(user).where(ticket_filter)))
    names = await _names(db, tickets)
    counts: Counter[str] = Counter()
    for t in tickets:
        for value in _values(t, field, custom, names):
            counts[value] += 1
    report = Report("distribution", f"Tickets by {field}", ["value", "count", "percent"])
    total = len(tickets)
    for value, n in counts.most_common():
        report.rows.append(
            {"value": value, "count": n, "percent": round(100 * n / total, 1) if total else 0}
        )
    report.summary = {"field": field, "tickets": total, "values": len(counts)}
    return report


async def _names(db: AsyncSession, tickets: list[Ticket]) -> dict[str, dict[Any, str]]:
    areas = dict((await db.execute(select(Area.id, Area.name))).all())
    milestones = dict((await db.execute(select(Milestone.id, Milestone.name))).all())
    statuses = dict((await db.execute(select(Status.id, Status.name))).all())
    users = dict((await db.execute(select(User.id, User.handle))).all())
    return {"area": areas, "milestone": milestones, "status": statuses, "assignee": users}


def _values(
    t: Ticket, field: str, custom: str | None, names: dict[str, dict[Any, str]]
) -> list[str]:
    """Empty values are '(none)'; tags give one value per tag."""
    none = "(none)"
    if custom is not None:
        value = (t.custom_fields or {}).get(custom)
        if isinstance(value, list):
            return [str(v) for v in value] or [none]
        return [str(value)] if value not in (None, "") else [none]
    if field == "tag":
        return list(t.tags) or [none]
    if field == "priority":
        return [t.priority.value]
    if field == "type":
        return [t.type.value]
    ref = {
        "area": t.area_id,
        "milestone": t.milestone_id,
        "status": t.status_id,
        "assignee": t.assignee_id,
    }[field]
    return [names[field].get(ref, none)] if ref is not None else [none]


async def milestone_progress(
    db: AsyncSession, user: User, milestone: Milestone, *, today: date
) -> Report:
    p = await forecast.milestone_progress(db, user, milestone, today=today)
    report = Report(
        "milestone_progress",
        f"Progress · {milestone.name}",
        ["metric", "value"],
    )
    summary = {
        "milestone": p.milestone,
        "target_date": p.target_date.isoformat() if p.target_date else None,
        "tickets": p.tickets,
        "done": p.done,
        "percent_by_count": p.percent_by_count,
        "hours_total": p.hours_total,
        "hours_done": p.hours_done,
        "percent_by_hours": p.percent_by_hours,
        "remaining_hours": p.remaining_hours,
        "throughput_hours_per_week": p.throughput_hours_per_week,
        "forecast_date": p.forecast_date.isoformat() if p.forecast_date else None,
        "state": p.state,
        "reason": p.reason,
    }
    report.rows = [{"metric": k, "value": v} for k, v in summary.items()]
    report.summary = summary
    return report


async def time_report(db: AsyncSession, user: User, *, ticket_filter: Any, by: str) -> Report:
    """Original estimate against time spent, per ticket or grouped; and who went over."""
    if by not in TIME_GROUPS:
        raise fail("by", f"Group time by {', '.join(TIME_GROUPS)}.")
    rows = list(
        (
            await db.execute(
                search.base_query(user)
                .where(ticket_filter)
                .with_only_columns(Project.key, Ticket)
                .order_by(Project.key, Ticket.number)
            )
        ).all()
    )
    names = await _names(db, [t for _, t in rows])
    groups: dict[str, list[Decimal]] = {}
    over: list[dict[str, Any]] = []
    for project_key, t in rows:
        key = f"{project_key}-{t.number}"
        original = t.original_estimate_hours or Decimal(0)
        spent = spent_hours(t)
        label = key if by == "ticket" else _values(t, by, None, names)[0]
        acc = groups.setdefault(label, [Decimal(0), Decimal(0)])
        acc[0] += original
        acc[1] += spent
        if t.original_estimate_hours is not None and spent > t.original_estimate_hours:
            over.append(
                {
                    "key": key,
                    "title": t.title,
                    "original_hours": hours(original),
                    "spent_hours": hours(spent),
                    "over_hours": hours(spent - original),
                }
            )
    report = Report(
        "time",
        f"Time by {by}",
        [by, "original_estimate_hours", "spent_hours", "difference_hours"],
    )
    for label, (original, spent) in groups.items():
        report.rows.append(
            {
                by: label,
                "original_estimate_hours": hours(original),
                "spent_hours": hours(spent),
                "difference_hours": hours(spent - original),
            }
        )
    report.summary = {
        "original_estimate_hours": hours(sum((g[0] for g in groups.values()), Decimal(0))),
        "spent_hours": hours(sum((g[1] for g in groups.values()), Decimal(0))),
        "over_estimate": over,
    }
    return report
