"""Reports: one entry point that resolves the scope (project, board, sprint, milestone) with
the viewer's permissions and runs the report. Every report returns rows plus a summary."""

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Milestone, Status, User
from radicle.docket.services import boards, search, sprints
from radicle.docket.services.access import project_access
from radicle.docket.services.reports import agile, general
from radicle.docket.services.reports.common import Report, fail, parse_workdays

__all__ = ["TYPES", "Params", "Report", "run", "to_csv"]

TYPES = (
    "burndown",
    "burnup",
    "velocity",
    "cfd",
    "control_chart",
    "sprint",
    "created_resolved",
    "distribution",
    "milestone_progress",
    "time",
)


@dataclass
class Params:
    project: str | None = None
    board: uuid.UUID | None = None
    sprint: uuid.UUID | None = None
    milestone: str | None = None
    q: str | None = None
    start: date | None = None
    end: date | None = None
    field: str | None = None
    interval: str = "day"
    by: str = "ticket"
    count: int = 6


@dataclass
class Scope:
    ticket_filter: ColumnElement[bool]
    statuses: list[Status]
    board: Any = None
    project: Any = None


async def _scope(db: AsyncSession, user: User, p: Params, tz: str) -> Scope:
    """Tickets of a board (its source) or a project, plus the extra RQL."""
    extra = f" AND ({p.q})" if p.q and p.q.strip() else ""
    if p.board is not None:
        ba = await boards.load_board(db, user, p.board)
        source = ba.board.source_rql.strip()
        rql = f"({source}){extra}" if source else extra.removeprefix(" AND ")
        compiled = await search.compile_rql(db, user, rql, timezone=tz)
        statuses = await boards.scope_statuses(db, ba.board)
        return Scope(compiled.where, statuses, board=ba.board, project=ba.project)
    if p.project:
        access = await project_access(db, user, p.project)
        compiled = await search.compile_rql(
            db, user, f"project = {access.project.key}{extra}", timezone=tz
        )
        statuses = list(
            await db.scalars(select(Status).where(Status.project_id == access.project.id))
        )
        return Scope(compiled.where, statuses, project=access.project)
    raise fail("project", "Say which tickets: project=<key> or board=<id>.")


async def _milestone(db: AsyncSession, user: User, p: Params) -> Milestone:
    if not p.project or not p.milestone:
        raise fail("milestone", "Give the project key and the milestone name.")
    access = await project_access(db, user, p.project)
    milestone = await db.scalar(
        select(Milestone).where(
            Milestone.project_id == access.project.id,
            func.lower(Milestone.name) == p.milestone.lower(),
        )
    )
    if milestone is None:
        raise fail("milestone", f"Milestone '{p.milestone}' does not exist in {p.project.upper()}.")
    return milestone


def _range(p: Params, today: date, days: int) -> tuple[date, date]:
    end = p.end or today
    return p.start or end - timedelta(days=days - 1), end


async def run(
    db: AsyncSession, user: User, kind: str, p: Params, *, today: date, tz: str, workdays: str
) -> Report:
    if kind not in TYPES:
        raise fail("type", f"Unknown report '{kind}'. Reports: {', '.join(TYPES)}.")
    if kind in ("burndown", "sprint") or (kind == "burnup" and p.sprint is not None):
        if p.sprint is None:
            raise fail("sprint", f"The {kind} report needs sprint=<id>.")
        _, sprint = await sprints.load_sprint(db, user, p.sprint)
        if kind == "burndown":
            return await agile.burndown(
                db, user, sprint, today=today, tz=tz, workdays=parse_workdays(workdays)
            )
        if kind == "sprint":
            return await agile.sprint_report(db, user, sprint)
        return await agile.burnup(
            db, user, sprint=sprint, start=p.start, end=p.end, today=today, tz=tz
        )
    if kind == "burnup":
        milestone = await _milestone(db, user, p)
        return await agile.burnup(
            db, user, milestone=milestone, start=p.start, end=p.end, today=today, tz=tz
        )
    if kind == "milestone_progress":
        return await general.milestone_progress(
            db, user, await _milestone(db, user, p), today=today
        )
    if kind == "velocity":
        if p.board is None:
            raise fail("board", "Velocity needs board=<id> of a Scrum board.")
        ba = await boards.load_board(db, user, p.board)
        return await agile.velocity(db, user, ba.board, count=max(1, min(p.count, 20)))
    scope = await _scope(db, user, p, tz)
    if kind == "cfd":
        start, end = _range(p, today, 30)
        return await agile.cumulative_flow(
            db,
            user,
            ticket_filter=scope.ticket_filter,
            statuses=scope.statuses,
            start=start,
            end=end,
            tz=tz,
        )
    if kind == "control_chart":
        start, end = _range(p, today, 90)
        return await agile.control_chart(
            db, user, ticket_filter=scope.ticket_filter, start=start, end=end, tz=tz
        )
    if kind == "created_resolved":
        start, end = _range(p, today, 30)
        return await general.created_vs_resolved(
            db,
            user,
            ticket_filter=scope.ticket_filter,
            start=start,
            end=end,
            interval=p.interval,
            tz=tz,
        )
    if kind == "distribution":
        if not p.field:
            raise fail("field", "Say which field to count by, e.g. field=area.")
        return await general.distribution(
            db, user, ticket_filter=scope.ticket_filter, field=p.field
        )
    return await general.time_report(db, user, ticket_filter=scope.ticket_filter, by=p.by)


def to_csv(report: Report) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=report.columns, extrasaction="ignore")
    writer.writeheader()
    for row in report.rows:
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return out.getvalue()
