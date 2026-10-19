from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from radicle.api.schemas.common import Input, UtcDatetime
from radicle.db.models import Priority, Resolution, StatusCategory, TicketType, UserKind


class UserRef(BaseModel):
    handle: str
    display_name: str
    kind: UserKind


class StatusRef(BaseModel):
    name: str
    category: StatusCategory


class TicketRef(BaseModel):
    key: str
    title: str
    type: TicketType
    status: StatusRef


class ChecklistItemOut(BaseModel):
    index: int
    text: str
    checked: bool
    assignee: str | None
    assignee_unknown: bool = False


class LinkOut(BaseModel):
    id: str
    type: str
    label: str = Field(description="As read from this ticket, e.g. 'is blocked by'")
    ticket: TicketRef


class WarningOut(BaseModel):
    code: str
    message: str
    by: list[str] | None = None


class TicketOut(BaseModel):
    key: str
    project: str
    type: TicketType
    title: str
    description_md: str
    status: StatusRef
    resolution: Resolution | None
    priority: Priority
    area: str | None
    milestone: str | None
    parent: TicketRef | None
    assignee: UserRef | None
    collaborators: list[UserRef]
    reporter: UserRef
    due_date: date | None
    estimate_hours: float | None
    tags: list[str]
    checklist: list[ChecklistItemOut]
    links: list[LinkOut]
    children_count: int
    comments_count: int
    blocked: bool
    rank: str
    version: int
    created_at: UtcDatetime
    updated_at: UtcDatetime
    resolved_at: UtcDatetime | None
    deleted: bool = False
    warnings: list[WarningOut] = Field(default_factory=list)


class TicketCreate(Input):
    type: TicketType
    title: str
    description_md: str = ""
    area: str | None = Field(default=None, description="Area name; required for task and bug")
    milestone: str | None = None
    priority: Priority = Priority.medium
    assignee: str | None = Field(default=None, description="Handle of a member or agent")
    collaborators: list[str] = Field(default_factory=list)
    parent: str | None = Field(default=None, description="Parent ticket key, e.g. PA-4")
    due_date: date | None = None
    estimate_hours: float | None = None
    tags: list[str] = Field(default_factory=list)


class TicketPatch(Input):
    """Only the fields you send change; null clears a field."""

    title: str | None = None
    description_md: str | None = None
    priority: Priority | None = None
    area: str | None = None
    milestone: str | None = None
    parent: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    estimate_hours: float | None = None
    tags: list[str] | None = None
    expected_version: int | None = Field(
        default=None, description="Required unless sent as the If-Match header"
    )


class ChecklistPatch(Input):
    checked: bool


class EventOut(BaseModel):
    id: int
    event_type: str
    field: str | None
    old_value: Any
    new_value: Any
    actor: UserRef
    created_at: UtcDatetime


class TicketSummary(BaseModel):
    """Compact row for lists and search results."""

    key: str
    title: str
    type: TicketType
    status: StatusRef
    resolution: Resolution | None
    priority: Priority
    assignee: UserRef | None
    area: str | None
    milestone: str | None
    tags: list[str]
    blocked: bool
    due_date: date | None
    estimate_hours: float | None
    checklist_done: int
    checklist_total: int
    rank: str
    updated_at: UtcDatetime
