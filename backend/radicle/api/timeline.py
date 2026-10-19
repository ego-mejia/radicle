from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from radicle.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.api.schemas.timeline import (
    DependencyOut,
    MilestoneMarker,
    TimelineGroup,
    TimelineOut,
    TimelineTicket,
)
from radicle.api.ticket_views import summaries_out
from radicle.db.models import Ticket
from radicle.services import periods, timeline
from radicle.services.access import project_access

router = APIRouter(tags=["timeline"])


async def _tickets(db: Db, items: list[Ticket]) -> list[TimelineTicket]:
    summaries = await summaries_out(db, items)
    return [
        TimelineTicket(**s.model_dump(), version=t.version)
        for t, s in zip(items, summaries, strict=True)
    ]


@router.get("/projects/{key}/timeline", response_model=TimelineOut)
async def get_timeline(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    group_by: Literal["milestone", "area"] = "milestone",
    q: str | None = Query(default=None, description="Extra RQL, combined with AND"),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
) -> TimelineOut:
    """Tickets by start_date and due_date, grouped by milestone (with target and forecast)
    or area, and Blocks dependencies with conflicts marked."""
    access = await project_access(db, principal.user, key)
    data = await timeline.timeline(
        db,
        principal.user,
        access.project,
        group_by=group_by,
        q=q,
        start=from_,
        end=to,
        today=periods.today(settings.timezone),
        timezone=settings.timezone,
    )
    keys: dict[object, str] = {}
    groups = []
    for g in data.groups:
        tickets = await _tickets(db, g.tickets)
        keys.update({t.id: s.key for t, s in zip(g.tickets, tickets, strict=True)})
        marker = (
            MilestoneMarker(
                name=g.milestone.name,
                target_date=g.milestone.target_date,
                forecast_date=g.progress.forecast_date,
                state=g.progress.state,
                percent_by_hours=g.progress.percent_by_hours,
            )
            if g.milestone and g.progress
            else None
        )
        groups.append(TimelineGroup(key=g.key, label=g.label, milestone=marker, tickets=tickets))
    return TimelineOut(
        group_by=group_by,
        groups=groups,
        undated=await _tickets(db, data.undated),
        dependencies=[
            DependencyOut(blocker=keys[d.blocker], blocked=keys[d.blocked], conflict=d.conflict)
            for d in data.dependencies
        ],
        truncated=data.truncated,
    )
