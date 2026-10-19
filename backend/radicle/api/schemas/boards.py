from typing import Any

from pydantic import Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.api.schemas.sprints import SprintOut
from radicle.api.schemas.tickets import TicketSummary, WarningOut
from radicle.db.models import BoardKind, Resolution, StatusCategory, Swimlane, TicketType, WipMode


class ColumnConf(Input):
    name: str
    status_ids: list[str] = Field(default_factory=list)
    categories: list[StatusCategory] = Field(
        default_factory=list, description="Every status of these categories, now and later"
    )
    wip_limit: int | None = None


class ColumnOut(Output):
    name: str
    status_ids: list[str]
    categories: list[StatusCategory]
    wip_limit: int | None


class QuickFilterOut(Output):
    id: str
    name: str
    rql: str
    position: int


class QuickFilterIn(Input):
    name: str
    rql: str
    position: int | None = None


class BoardStatus(Output):
    id: str
    name: str
    type: TicketType
    category: StatusCategory


class BoardOut(Output):
    id: str
    project: str | None
    name: str
    kind: BoardKind
    source_rql: str
    columns: list[ColumnOut]
    wip_mode: WipMode
    swimlane_by: Swimlane
    card_fields: list[str]
    done_window_days: int
    quick_filters: list[QuickFilterOut]
    statuses: list[BoardStatus] = Field(description="Statuses in the board's scope")
    unmapped_statuses: list[BoardStatus] = Field(
        description="Statuses in no column: their tickets do not show"
    )
    created_at: UtcDatetime
    updated_at: UtcDatetime


class BoardCreate(Input):
    name: str
    kind: BoardKind = BoardKind.kanban
    source_rql: str | None = Field(default=None, description="Default: the whole project")
    columns: list[ColumnConf] | None = None
    wip_mode: WipMode = WipMode.soft
    swimlane_by: Swimlane = Swimlane.none
    card_fields: list[str] = Field(default_factory=lambda: ["priority", "assignee", "tags"])
    done_window_days: int = 14


class BoardPatch(Input):
    name: str | None = None
    kind: BoardKind | None = None
    source_rql: str | None = None
    columns: list[ColumnConf] | None = None
    wip_mode: WipMode | None = None
    swimlane_by: Swimlane | None = None
    card_fields: list[str] | None = None
    done_window_days: int | None = None


class Card(TicketSummary):
    lane: str = Field(description="Swimlane key; empty for 'none'")


class ColumnData(Output):
    index: int
    name: str
    wip_limit: int | None
    count: int = Field(description="All tickets in the column, not just this page")
    over_limit: bool
    done_only: bool
    tickets: list[Card]
    next_cursor: str | None


class LaneOut(Output):
    key: str
    label: str
    count: int


class BoardDataOut(Output):
    board: BoardOut
    swimlane_by: Swimlane
    lanes: list[LaneOut]
    columns: list[ColumnData]
    sprint: SprintOut | None = Field(
        default=None, description="Scrum boards: the active sprint, whose tickets they show"
    )


class BoardMoveIn(Input):
    ticket: str = Field(description="Ticket key")
    column: int = Field(description="Target column index")
    before: str | None = Field(default=None, description="Rank it right above this key")
    after: str | None = None
    transition: str | None = Field(
        default=None, description="Needed when several transitions reach the column"
    )
    resolution: Resolution | None = None
    comment: str | None = None
    fields: dict[str, Any] | None = None
    log_minutes: int | None = Field(default=None, description="Time to log with the move")
    force: bool = Field(default=False, description="Admins: go over a hard WIP limit")


class BoardMoveOut(Output):
    ticket: TicketSummary
    warnings: list[WarningOut]
