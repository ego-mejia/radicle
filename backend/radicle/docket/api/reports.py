from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.docket.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.docket.api.schemas.common import Output
from radicle.docket.services import periods, reports

router = APIRouter(tags=["reports"])


class ReportOut(Output):
    type: str
    title: str
    columns: list[str] = Field(description="Row keys, in order; also the CSV header")
    rows: list[dict[str, Any]]
    summary: dict[str, Any]


def _params(
    project: str | None,
    board: UUID | None,
    sprint: UUID | None,
    milestone: str | None,
    q: str | None,
    from_: date | None,
    to: date | None,
    field: str | None,
    interval: str,
    by: str,
    count: int,
) -> reports.Params:
    return reports.Params(
        project=project,
        board=board,
        sprint=sprint,
        milestone=milestone,
        q=q,
        start=from_,
        end=to,
        field=field,
        interval=interval,
        by=by,
        count=count,
    )


async def _run(
    db: Db, principal: CurrentPrincipal, settings: AppSettings, kind: str, p: reports.Params
) -> reports.Report:
    return await reports.run(
        db,
        principal.user,
        kind,
        p,
        today=periods.today(settings.timezone),
        tz=settings.timezone,
        workdays=settings.workdays,
    )


@router.get("/reports/{kind}.csv", response_class=Response)
async def report_csv(
    kind: str,
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    project: str | None = None,
    board: UUID | None = None,
    sprint: UUID | None = None,
    milestone: str | None = None,
    q: str | None = None,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    field: str | None = None,
    interval: str = "day",
    by: str = "ticket",
    count: int = 6,
) -> Response:
    """The report's rows as CSV."""
    p = _params(project, board, sprint, milestone, q, from_, to, field, interval, by, count)
    report = await _run(db, principal, settings, kind, p)
    return Response(
        reports.to_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'},
    )


@router.get("/reports/{kind}", response_model=ReportOut)
async def report(
    kind: str,
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    project: str | None = Query(default=None, description="Project key"),
    board: UUID | None = None,
    sprint: UUID | None = None,
    milestone: str | None = Query(default=None, description="Milestone name (with project)"),
    q: str | None = Query(default=None, description="Extra RQL, combined with AND"),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    field: str | None = Query(default=None, description="distribution: area, priority, cf.<key>…"),
    interval: str = Query(default="day", description="created_resolved: day or week"),
    by: str = Query(default="ticket", description="time: ticket, milestone, area or assignee"),
    count: int = Query(default=6, description="velocity: how many closed sprints"),
) -> ReportOut:
    """burndown, burnup, velocity, cfd, control_chart, sprint, created_resolved,
    distribution, milestone_progress or time. Only tickets you can see count."""
    p = _params(project, board, sprint, milestone, q, from_, to, field, interval, by, count)
    r = await _run(db, principal, settings, kind, p)
    return ReportOut(type=r.type, title=r.title, columns=r.columns, rows=r.rows, summary=r.summary)
