"""Agile reports: burndown, burnup, velocity, cumulative flow, control chart, sprint report.
Everything is in hours, since estimates are in hours."""

import uuid
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Board,
    Milestone,
    Project,
    Sprint,
    SprintCommitment,
    SprintState,
    SprintTicket,
    Status,
    StatusCategory,
    Ticket,
    TicketStatusPeriod,
    User,
)
from radicle.services import search, sprints
from radicle.services.periods import day_end
from radicle.services.reports.common import (
    Report,
    categories_at,
    day_ends,
    days_between,
    fail,
    hours,
    percentile,
    remaining_at,
)


def _sprint_days(sprint: Sprint) -> tuple[date, date]:
    if sprint.start_date is None or sprint.end_date is None:
        raise fail("sprint", f"'{sprint.name}' has no dates yet: start it first.")
    return sprint.start_date, sprint.end_date


async def _visible(db: AsyncSession, user: User, ids: set[uuid.UUID]) -> list[Ticket]:
    if not ids:
        return []
    return list(await db.scalars(search.base_query(user).where(Ticket.id.in_(ids))))


async def burndown(
    db: AsyncSession, user: User, sprint: Sprint, *, today: date, tz: str, workdays: set[int]
) -> Report:
    """Ideal: committed remaining down to 0 across the working days. Actual: remaining hours
    of the sprint's tickets at the end of each day (done counts 0). Scope changes marked."""
    start, end = _sprint_days(sprint)
    days = [d for d in days_between(start, end) if d.weekday() in workdays] or [start]
    commitments = list(
        await db.scalars(select(SprintCommitment).where(SprintCommitment.sprint_id == sprint.id))
    )
    committed = sum(
        hours(c.remaining_hours if c.remaining_hours is not None else c.estimate_hours)
        for c in commitments
    )
    rows = list(await db.scalars(select(SprintTicket).where(SprintTicket.sprint_id == sprint.id)))
    tickets = await _visible(db, user, {r.ticket_id for r in rows})
    visible = {t.id for t in tickets}
    shown = [d for d in days if d <= min(today, end)]
    ends = day_ends(shown, tz)
    remaining = await remaining_at(db, tickets, ends)
    categories = await categories_at(db, list(visible), ends)
    closed_at = sprint.completed_at

    report = Report(
        "burndown",
        f"Burndown · {sprint.name}",
        ["date", "ideal_hours", "remaining_hours", "scope_change"],
    )
    n = len(days)
    for i, day in enumerate(days):
        ideal = round(committed * (1 - i / (n - 1)), 2) if n > 1 else 0.0
        row: dict[str, Any] = {"date": day.isoformat(), "ideal_hours": ideal}
        if day in shown:
            j = shown.index(day)
            moment = ends[j]
            total = 0.0
            for r in rows:
                if r.ticket_id not in visible or r.added_at >= moment:
                    continue
                if r.removed_at is not None and r.removed_at < moment and r.removed_at != closed_at:
                    continue
                if categories[r.ticket_id][j] is StatusCategory.done:
                    continue
                total += hours(remaining[r.ticket_id][j])
            row["remaining_hours"] = round(total, 2)
        else:
            row["remaining_hours"] = None
        row["scope_change"] = any(
            (r.added_after_start and r.added_at.astimezone(ZoneInfo(tz)).date() == day)
            or (
                r.removed_at is not None
                and r.removed_at != closed_at
                and r.removed_at.astimezone(ZoneInfo(tz)).date() == day
            )
            for r in rows
            if r.ticket_id in visible
        )
        report.rows.append(row)
    report.summary = {
        "sprint": sprint.name,
        "committed_hours": committed,
        "remaining_hours": next(
            (
                r["remaining_hours"]
                for r in reversed(report.rows)
                if r["remaining_hours"] is not None
            ),
            committed,
        ),
        "working_days": n,
    }
    return report


async def burnup(
    db: AsyncSession,
    user: User,
    *,
    sprint: Sprint | None = None,
    milestone: Milestone | None = None,
    start: date | None = None,
    end: date | None = None,
    today: date,
    tz: str,
) -> Report:
    """Scope (estimate hours in scope) and completed (estimate of the done ones), per day."""
    if sprint is not None:
        first, last = _sprint_days(sprint)
        rows = list(
            await db.scalars(select(SprintTicket).where(SprintTicket.sprint_id == sprint.id))
        )
        tickets = await _visible(db, user, {r.ticket_id for r in rows})
        title = sprint.name
    elif milestone is not None:
        tickets = list(
            await db.scalars(search.base_query(user).where(Ticket.milestone_id == milestone.id))
        )
        rows = []
        first = start or min(
            (t.created_at.astimezone(ZoneInfo(tz)).date() for t in tickets), default=today
        )
        last = end or max(today, milestone.target_date or today)
        title = milestone.name
    else:
        raise fail("sprint", "Burnup needs a sprint or a milestone.")
    first, last = start or first, end or last
    days = [d for d in days_between(first, last) if d <= today]
    ends = day_ends(days, tz)
    categories = await categories_at(db, [t.id for t in tickets], ends)
    report = Report("burnup", f"Burnup · {title}", ["date", "scope_hours", "completed_hours"])
    for j, day in enumerate(days):
        moment = ends[j]
        scope = done = 0.0
        for t in tickets:
            if categories[t.id][j] is None:
                continue  # did not exist yet
            if sprint is not None and not any(
                r.ticket_id == t.id
                and r.added_at < moment
                and (
                    r.removed_at is None
                    or r.removed_at >= moment
                    or r.removed_at == sprint.completed_at
                )
                for r in rows
            ):
                continue
            scope += hours(t.estimate_hours)
            if categories[t.id][j] is StatusCategory.done:
                done += hours(t.estimate_hours)
        report.rows.append(
            {
                "date": day.isoformat(),
                "scope_hours": round(scope, 2),
                "completed_hours": round(done, 2),
            }
        )
    last_row = report.rows[-1] if report.rows else {"scope_hours": 0, "completed_hours": 0}
    report.summary = {
        "scope_hours": last_row["scope_hours"],
        "completed_hours": last_row["completed_hours"],
    }
    return report


async def velocity(db: AsyncSession, user: User, board: Board, *, count: int = 6) -> Report:
    """Committed against completed hours for the last closed sprints; average of the last 3."""
    closed = list(
        await db.scalars(
            select(Sprint)
            .where(Sprint.board_id == board.id, Sprint.state == SprintState.closed)
            .order_by(Sprint.completed_at.desc())
            .limit(count)
        )
    )
    closed.reverse()
    report = Report(
        "velocity",
        f"Velocity · {board.name}",
        ["sprint", "committed_hours", "completed_hours"],
    )
    for s in closed:
        data = await sprints.report(db, s)
        report.rows.append(
            {
                "sprint": s.name,
                "committed_hours": hours(data["committed_hours"]),
                "completed_hours": hours(data["completed_hours"]),
            }
        )
    last3 = [r["completed_hours"] for r in report.rows[-3:]]
    report.summary = {
        "average_completed_hours": round(sum(last3) / len(last3), 2) if last3 else None,
        "sprints": len(report.rows),
    }
    return report


async def cumulative_flow(
    db: AsyncSession,
    user: User,
    *,
    ticket_filter: Any,
    statuses: list[Status],
    start: date,
    end: date,
    tz: str,
) -> Report:
    """Tickets per status at the end of each day, stacked in workflow order.

    A period entered on local day X and left on local day Y counts on days X to Y-1. The
    database groups periods by (status, X, Y) and the days are filled with a running sum,
    so a year of a big project costs one pass over its periods."""
    days = days_between(start, end)
    first_end, last_end = day_ends([start, end], tz)
    visible = search.base_query(user).where(ticket_filter).with_only_columns(Ticket.id)
    entered = func.date(func.timezone(tz, TicketStatusPeriod.entered_at))
    exited = func.date(func.timezone(tz, TicketStatusPeriod.exited_at))
    rows = await db.execute(
        select(TicketStatusPeriod.status_id, entered, exited, func.count())
        .where(
            TicketStatusPeriod.ticket_id.in_(visible),
            TicketStatusPeriod.entered_at < last_end,
            or_(
                TicketStatusPeriod.exited_at.is_(None),
                TicketStatusPeriod.exited_at >= first_end,
            ),
        )
        .group_by(TicketStatusPeriod.status_id, entered, exited)
    )
    n = len(days)
    diff: dict[uuid.UUID | None, list[int]] = {}
    for status_id, x, y, count in rows:
        lo = max((x - start).days, 0)
        hi = n - 1 if y is None else min((y - start).days - 1, n - 1)
        if lo > hi:
            continue
        line = diff.setdefault(status_id, [0] * (n + 1))
        line[lo] += count
        line[hi + 1] -= count
    running = {sid: 0 for sid in diff}
    per_day: list[dict[uuid.UUID | None, int]] = []
    for i in range(n):
        for sid, line in diff.items():
            running[sid] += line[i]
        per_day.append(dict(running))
    order = _workflow_order(statuses)
    names = [name for name, _ in order]
    report = Report("cfd", "Cumulative flow", ["date", *names])
    for i, day in enumerate(days):
        row: dict[str, Any] = {"date": day.isoformat()}
        for name, ids in order:
            row[name] = sum(per_day[i].get(sid, 0) for sid in ids)
        report.rows.append(row)
    report.summary = {
        "statuses": [{"name": n, "category": c} for n, c in _categories(statuses, names)],
        "days": len(days),
    }
    return report


def _workflow_order(statuses: list[Status]) -> list[tuple[str, list[uuid.UUID]]]:
    """Statuses by name (types share names), ordered by category then position."""
    rank = {StatusCategory.todo: 0, StatusCategory.in_progress: 1, StatusCategory.done: 2}
    groups: dict[str, tuple[tuple[int, int], list[uuid.UUID]]] = {}
    for s in statuses:
        key = (rank[s.category], s.position)
        current = groups.get(s.name)
        if current is None:
            groups[s.name] = (key, [s.id])
        else:
            groups[s.name] = (min(current[0], key), [*current[1], s.id])
    return [(name, ids) for name, (_, ids) in sorted(groups.items(), key=lambda kv: kv[1][0])]


def _categories(statuses: list[Status], names: list[str]) -> list[tuple[str, str]]:
    by_name = {s.name: s.category.value for s in statuses}
    return [(n, by_name[n]) for n in names]


async def control_chart(
    db: AsyncSession,
    user: User,
    *,
    ticket_filter: Any,
    start: date,
    end: date,
    tz: str,
) -> Report:
    """One point per ticket resolved in the range: cycle time (first entry to in progress to
    the last entry to done) and lead time (created to that entry), in days; rolling mean of
    the last 5 and percentiles 50, 85 and 95 of the cycle time."""
    days_between(start, end)
    since = day_end(start - timedelta(days=1), tz)
    until = day_end(end, tz)
    first_progress = (
        select(func.min(TicketStatusPeriod.entered_at))
        .where(
            TicketStatusPeriod.ticket_id == Ticket.id,
            TicketStatusPeriod.category == StatusCategory.in_progress,
        )
        .scalar_subquery()
    )
    last_done = (
        select(func.max(TicketStatusPeriod.entered_at))
        .where(
            TicketStatusPeriod.ticket_id == Ticket.id,
            TicketStatusPeriod.category == StatusCategory.done,
        )
        .scalar_subquery()
    )
    rows = await db.execute(
        search.base_query(user)
        .where(ticket_filter, Status.category == StatusCategory.done)
        .with_only_columns(Project.key, Ticket, first_progress, last_done)
    )
    points = []
    for project_key, ticket, progressed, done in rows:
        if done is None or not since <= done < until:
            continue
        cycle = (done - progressed).total_seconds() / 86400 if progressed else None
        lead = (done - ticket.created_at).total_seconds() / 86400
        points.append((done, f"{project_key}-{ticket.number}", cycle, lead))
    points.sort(key=lambda p: (p[0], p[1]))
    report = Report(
        "control_chart",
        "Control chart",
        ["key", "resolved", "cycle_days", "lead_days", "rolling_mean_days"],
    )
    window: list[float] = []
    for done, key, cycle, lead in points:
        if cycle is not None:
            window = [*window[-4:], cycle]
        report.rows.append(
            {
                "key": key,
                "resolved": done.isoformat(),
                "cycle_days": round(cycle, 2) if cycle is not None else None,
                "lead_days": round(lead, 2),
                "rolling_mean_days": round(sum(window) / len(window), 2) if window else None,
            }
        )
    cycles = [r["cycle_days"] for r in report.rows if r["cycle_days"] is not None]
    report.summary = {
        "tickets": len(report.rows),
        "p50_days": percentile(cycles, 50),
        "p85_days": percentile(cycles, 85),
        "p95_days": percentile(cycles, 95),
        "mean_days": round(sum(cycles) / len(cycles), 2) if cycles else None,
    }
    return report


async def sprint_report(db: AsyncSession, sprint: Sprint) -> Report:
    data = await sprints.report(db, sprint)
    report = Report(
        "sprint",
        f"Sprint report · {sprint.name}",
        ["outcome", "key", "title", "estimate_hours", "committed_hours", "remaining_hours"],
    )
    for outcome in ("completed", "not_completed", "added_after_start", "removed"):
        for item in data[outcome]:
            report.rows.append({"outcome": outcome, **item})
    report.summary = {
        k: data[k]
        for k in (
            "sprint",
            "goal",
            "goal_met",
            "start_date",
            "end_date",
            "committed_hours",
            "completed_hours",
        )
    }
    report.summary["counts"] = {
        k: len(data[k]) for k in ("completed", "not_completed", "added_after_start", "removed")
    }
    return report
