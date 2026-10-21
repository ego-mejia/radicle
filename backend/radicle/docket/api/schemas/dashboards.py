from typing import Any

from pydantic import Field

from radicle.docket.api.schemas.common import Input, Output, UtcDatetime
from radicle.docket.api.schemas.tickets import TicketSummary
from radicle.docket.db.models import FilterVisibility


class Layout(Input):
    x: int
    y: int
    w: int
    h: int


class LayoutItem(Layout):
    id: str


class WidgetOut(Output):
    id: str
    widget_type: str
    title: str
    config: dict[str, Any]
    layout: dict[str, int]


class DashboardOut(Output):
    id: str
    name: str
    owner: str = Field(description="Owner handle")
    visibility: FilterVisibility
    project: str | None
    is_project_default: bool
    can_edit: bool
    updated_at: UtcDatetime


class DashboardDetail(DashboardOut):
    widgets: list[WidgetOut]
    refresh_seconds: int = Field(description="How often the UI refreshes the widgets")


class DashboardCreate(Input):
    name: str
    visibility: FilterVisibility = FilterVisibility.private
    project: str | None = Field(default=None, description="Project key, for project visibility")


class DashboardPatch(Input):
    name: str | None = None
    visibility: FilterVisibility | None = None
    project: str | None = None
    layout: list[LayoutItem] | None = Field(
        default=None, description="New positions of several widgets at once (after a drag)"
    )


class WidgetCreate(Input):
    widget_type: str = Field(
        description="filter_results, count, distribution, milestone_progress, "
        "created_vs_resolved, sprint_burndown, cumulative_flow, blocked_tickets, my_tickets, "
        "markdown"
    )
    title: str
    config: dict[str, Any] = Field(default_factory=dict)
    layout: Layout | None = Field(default=None, description="Default: a new row at the bottom")


class WidgetPatch(Input):
    title: str | None = None
    config: dict[str, Any] | None = None
    layout: Layout | None = None


class WidgetTicket(TicketSummary):
    blocked_by: list[str] = Field(default_factory=list, description="Open blockers you can see")


class WidgetDataOut(Output):
    widget_id: str
    widget_type: str
    data: dict[str, Any]
    tickets: list[WidgetTicket] | None = None
    total: int | None = None
