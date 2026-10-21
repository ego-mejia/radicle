from datetime import date

from pydantic import Field

from radicle.docket.api.schemas.tickets import TicketSummary
from radicle.platform.api.schemas import Output


class TimelineTicket(TicketSummary):
    version: int = Field(description="Send it as If-Match when changing the dates")


class MilestoneMarker(Output):
    name: str
    target_date: date | None
    forecast_date: date | None
    state: str = Field(description="on_track, at_risk, no_forecast or done")
    percent_by_hours: float


class TimelineGroup(Output):
    key: str = Field(description="Milestone or area id; empty for tickets without one")
    label: str
    milestone: MilestoneMarker | None
    tickets: list[TimelineTicket]


class DependencyOut(Output):
    blocker: str = Field(description="Key of the ticket that blocks")
    blocked: str
    conflict: bool = Field(description="The blocker ends after the blocked ticket begins")


class TimelineOut(Output):
    group_by: str
    groups: list[TimelineGroup]
    undated: list[TimelineTicket] = Field(description="Tickets without start or due date")
    dependencies: list[DependencyOut]
    truncated: bool = Field(description="More than 2,000 tickets: narrow the query")
