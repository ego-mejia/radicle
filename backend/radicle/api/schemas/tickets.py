from datetime import date
from typing import Any, Literal

from pydantic import Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.db.models import (
    Classification,
    Origin,
    Priority,
    RemainingMode,
    Resolution,
    StatusCategory,
    TicketType,
    UserKind,
)


class UserRef(Output):
    handle: str
    display_name: str
    kind: UserKind


class StatusRef(Output):
    name: str
    category: StatusCategory


class TicketRef(Output):
    """Null key, title, type and status with `restricted`: a ticket you may not see."""

    key: str | None
    title: str | None
    type: TicketType | None
    status: StatusRef | None
    restricted: bool = False


class ChecklistItemOut(Output):
    index: int
    text: str
    checked: bool
    assignee: str | None
    assignee_unknown: bool = False


class LinkOut(Output):
    id: str
    type: str
    label: str = Field(description="As read from this ticket, e.g. 'is blocked by'")
    ticket: TicketRef


class WarningOut(Output):
    code: str
    message: str
    by: list[str] | None = None


class AttachmentOut(Output):
    id: str
    ticket: str
    filename: str
    mime_type: str = Field(description="Detected from the content, not the name")
    size_bytes: int
    is_image: bool
    width: int | None
    height: int | None
    uploader: UserRef
    comment_id: str | None
    created_at: UtcDatetime
    url: str = Field(description="Signed download URL, valid for 5 minutes")
    thumb_url: str | None = Field(description="320 px webp, once the worker made it")
    preview_url: str | None = Field(description="1280 px webp, once the worker made it")
    markdown: str = Field(description="Paste it in a description or comment")


class TicketOut(Output):
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
    start_date: date | None
    due_date: date | None
    estimate_hours: float | None
    original_estimate_hours: float | None = Field(description="The first estimate; never changes")
    remaining_hours: float | None
    remaining_mode: RemainingMode = Field(description="auto: estimate - spent; manual: as set")
    spent_hours: float
    vote_count: int
    voted_by_me: bool
    tags: list[str]
    custom_fields: dict[str, Any] = Field(
        description="Values by field key; user fields as handles. Only fields that apply."
    )
    checklist: list[ChecklistItemOut]
    links: list[LinkOut]
    attachments: list[AttachmentOut]
    children_count: int
    comments_count: int
    blocked: bool
    rank: str
    version: int
    created_at: UtcDatetime
    updated_at: UtcDatetime
    resolved_at: UtcDatetime | None
    deleted: bool = False
    moved_from: str | None = Field(
        default=None, description="Set when you asked for an old key of a moved ticket"
    )
    security_level: str | None = Field(
        default=None, description="Who may see it is limited by this level"
    )
    origin: Origin | None = Field(default=None, description="Inbox: team or user (public form)")
    classification: Classification | None = None
    impact: int | None = None
    effort: int | None = None
    converted_at: UtcDatetime | None = Field(
        default=None, description="When it came out of the inbox as a task or bug"
    )
    submitter_name: str | None = None
    submitter_email: str | None = None
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
    start_date: date | None = None
    due_date: date | None = None
    estimate_hours: float | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description='By field key, e.g. {"environment": "prod"}'
    )
    classification: Classification | None = Field(
        default=None, description="Drafts only, required: idea, experiment, complaint, suggestion"
    )


class TicketPatch(Input):
    """Only the fields you send change; null clears a field."""

    title: str | None = None
    description_md: str | None = None
    priority: Priority | None = None
    area: str | None = None
    milestone: str | None = None
    parent: str | None = None
    assignee: str | None = None
    start_date: date | None = None
    due_date: date | None = None
    estimate_hours: float | None = None
    remaining_hours: float | None = Field(
        default=None, description="Setting it switches remaining_mode to manual"
    )
    remaining_mode: Literal["auto"] | None = Field(
        default=None, description="Send auto to go back to estimate minus spent"
    )
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = Field(
        default=None, description="Only the keys you send change; null clears a value"
    )
    security_level: str | None = Field(
        default=None,
        description="Security level name; null makes the ticket public to the project. "
        "Needs ticket.set_security",
    )
    classification: Classification | None = Field(
        default=None, description="Inbox: needs inbox.triage"
    )
    impact: int | None = Field(default=None, description="Inbox, 1 to 5: needs inbox.triage")
    effort: int | None = Field(default=None, description="Inbox, 1 to 5: needs inbox.triage")
    expected_version: int | None = Field(
        default=None, description="Required unless sent as the If-Match header"
    )


class ChecklistPatch(Input):
    checked: bool


class EventOut(Output):
    id: int
    event_type: str
    field: str | None
    old_value: Any
    new_value: Any
    actor: UserRef
    created_at: UtcDatetime


class TicketSummary(Output):
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
    custom_fields: dict[str, Any]
    blocked: bool
    start_date: date | None
    due_date: date | None
    estimate_hours: float | None
    spent_hours: float
    vote_count: int
    checklist_done: int
    checklist_total: int
    rank: str
    updated_at: UtcDatetime
    created_at: UtcDatetime | None = None
    origin: Origin | None = None
    classification: Classification | None = None
    impact: int | None = None
    effort: int | None = None
    converted: bool = False


class RuleFailureOut(Output):
    rule: str
    message: str


class TransitionOption(Output):
    name: str
    to_status: str
    category: StatusCategory
    allowed_resolutions: list[Resolution] | None = Field(
        description="Set when the target is a done status; pick one of these"
    )
    available: bool = Field(default=True, description="False only with include_unavailable")
    reasons: list[RuleFailureOut] = Field(
        default_factory=list, description="Conditions that fail for you"
    )
    requires_comment: bool = False
    has_screen: bool = Field(
        default=False,
        description="Asks for fields: see /projects/{key}/schema?operation=transition",
    )


class TransitionIn(Input):
    to_status: str = Field(description="Target status name, e.g. 'In Progress'")
    resolution: Resolution | None = None
    transition: str | None = Field(
        default=None, description="Transition name, only needed when several reach the target"
    )
    comment: str | None = Field(
        default=None, description="Saved as a comment; required by comment_required rules"
    )
    force: bool = Field(
        default=False, description="Admins only: move a blocked ticket despite policy enforce"
    )
    log_minutes: int | None = Field(
        default=None, ge=1, le=1440, description="Log time spent in the same move"
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description='Values for the transition\'s screen, e.g. {"cf.environment": "prod"}',
    )


class TypeChangeIn(Input):
    type: TicketType
    area: str | None = Field(
        default=None, description="Required when moving to task or bug without an area"
    )


class LinkCreate(Input):
    type: str = Field(description="blocks, relates_to, duplicates or clones")
    target: str = Field(description="Target ticket key, e.g. PA-4")


class ReactionOut(Output):
    emoji: str
    count: int
    users: list[str]


class CommentOut(Output):
    id: str
    ticket: str
    author: UserRef
    body_md: str
    created_at: UtcDatetime
    edited_at: UtcDatetime | None
    deleted: bool
    reactions: list[ReactionOut] = Field(default_factory=list)


class CommentIn(Input):
    body_md: str


class WorklogOut(Output):
    id: str
    ticket: str
    user: UserRef
    minutes: int
    started_at: UtcDatetime
    description: str | None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class WorklogIn(Input):
    minutes: int = Field(ge=1, le=1440)
    started_at: UtcDatetime | None = Field(default=None, description="Default: now")
    description: str | None = None


class WorklogPatch(Input):
    minutes: int | None = Field(default=None, ge=1, le=1440)
    started_at: UtcDatetime | None = None
    description: str | None = Field(default=None, description="null clears it")


class VoteOut(Output):
    vote_count: int
    voted_by_me: bool
