from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field

from radicle.docket.api.schemas.common import Input, Output, UtcDatetime
from radicle.docket.api.schemas.tickets import TicketSummary
from radicle.docket.db.models import SprintState


class SprintOut(Output):
    id: str
    board_id: str
    name: str
    goal: str | None
    state: SprintState
    start_date: date | None
    end_date: date | None
    capacity_hours: float | None
    started_at: UtcDatetime | None
    completed_at: UtcDatetime | None
    position: int
    goal_met: bool | None
    ticket_count: int = Field(description="Tickets you can see")
    done_count: int
    estimate_hours: float
    remaining_hours: float
    unestimated_count: int = Field(description="Tickets without an estimate")
    over_capacity: bool


class SprintDetail(SprintOut):
    tickets: list[TicketSummary]


class SprintCreate(Input):
    name: str | None = Field(default=None, description="Default: Sprint N")
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: Decimal | None = None


class SprintPatch(Input):
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: Decimal | None = None
    position: int | None = None
    goal_met: bool | None = Field(default=None, description="Marked by hand in the report")


class SprintStart(Input):
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: Decimal | None = None


class SprintComplete(Input):
    move_unfinished_to: str = Field(
        default="backlog", description="A future sprint id of this board, or 'backlog'"
    )
    tag_backlog: bool = Field(default=True, description="Tag unfinished tickets #backlog")


class SprintCompleteOut(Output):
    sprint: SprintOut
    moved_to: SprintOut | None
    unfinished: list[str]


class SprintKeys(Input):
    keys: list[str] = Field(min_length=1, max_length=500)


class SprintKeysOut(Output):
    keys: list[str] = Field(description="Tickets that changed")


class ReportItem(Output):
    key: str
    title: str
    estimate_hours: float
    committed_hours: float
    remaining_hours: float


class SprintReport(Output):
    sprint: str
    goal: str | None
    goal_met: bool | None
    start_date: str | None
    end_date: str | None
    committed_hours: float
    completed_hours: float
    completed: list[ReportItem]
    not_completed: list[ReportItem]
    added_after_start: list[ReportItem]
    removed: list[ReportItem]


class BacklogOut(Output):
    items: list[TicketSummary]
    total: int


def report_out(data: dict[str, Any], visible: set[str]) -> SprintReport:
    """Drop tickets the viewer cannot see."""
    lists = ("completed", "not_completed", "added_after_start", "removed")
    filtered = {k: [i for i in data[k] if i["key"] in visible] for k in lists}
    return SprintReport(**{**data, **filtered})
