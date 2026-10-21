from datetime import date
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field

from radicle.docket.api.schemas.fields import CustomFieldOut
from radicle.docket.api.schemas.tickets import UserRef
from radicle.docket.db.models import (
    BlockedPolicy,
    MilestoneStatus,
    ProjectRole,
    Resolution,
    StatusCategory,
    TemplateMode,
    TicketType,
    UserKind,
)
from radicle.platform.api.schemas import Input, Output, UtcDatetime


class CategoryCounts(Output):
    todo: int = 0
    in_progress: int = 0
    done: int = 0


class ProjectOut(Output):
    key: str
    name: str
    description_md: str
    role: ProjectRole = Field(description="Your role in the project")
    archived: bool
    open_tickets: int = 0
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ProjectCreate(Input):
    key: str = Field(description="2-10 chars, uppercase letter then letters/digits. Immutable.")
    name: str
    description_md: str = ""
    template_id: UUID | None = Field(
        default=None, description="Template to copy the configuration from; default Radicle default"
    )
    template_mode: TemplateMode = Field(
        default=TemplateMode.linked,
        description="linked: template changes reach the project; detached: edit it freely",
    )


class ProjectPatch(Input):
    name: str | None = None
    description_md: str | None = None


ICON_HELP = "Name of an icon from the app's set, like rocket or shield (kebab case)"


class AreaOut(Output):
    model_config = ConfigDict(from_attributes=True)

    name: str
    color: str | None
    icon: str | None
    position: int
    archived: bool


class AreaCreate(Input):
    name: str
    color: str | None = None
    icon: str | None = Field(default=None, description=ICON_HELP)


class AreaPatch(Input):
    name: str | None = None
    color: str | None = Field(default=None, description="Hex like #4D7C0F; null clears it")
    icon: str | None = Field(default=None, description=f"{ICON_HELP}; null clears it")
    position: int | None = None
    archived: bool | None = None


class MilestoneOut(Output):
    name: str
    description_md: str
    target_date: date | None
    status: MilestoneStatus
    closed_at: UtcDatetime | None
    position: int
    counts: CategoryCounts = Field(description="Tickets per status category")


class MilestoneCreate(Input):
    name: str
    description_md: str = ""
    target_date: date | None = None


class MilestonePatch(Input):
    name: str | None = None
    description_md: str | None = None
    target_date: date | None = Field(default=None, description="null clears it")
    status: MilestoneStatus | None = None
    position: int | None = None


class MemberOut(Output):
    handle: str
    display_name: str
    kind: UserKind
    role: ProjectRole | None = Field(description="Direct role; null when only through groups")
    effective_role: ProjectRole = Field(description="Highest of the direct and group roles")
    groups: list[str] = Field(default_factory=list, description="Groups that bring them in")
    is_active: bool


class MemberPut(Input):
    role: ProjectRole


class CandidatePerson(Output):
    handle: str
    display_name: str
    kind: UserKind


class CandidateGroup(Output):
    name: str
    description: str


class MemberCandidates(Output):
    people: list[CandidatePerson]
    groups: list[CandidateGroup]


class StatusOut(Output):
    ref: str | None = Field(description="Stable slug; renames keep it")
    name: str
    category: StatusCategory
    is_initial: bool


class RuleOut(Output):
    kind: str = Field(description="condition, validator or post_function")
    rule_type: str
    config: dict[str, Any]


class TransitionOut(Output):
    ref: str | None
    from_ref: str | None
    to_ref: str
    name: str
    from_status: str | None = Field(description="null = from any status not in done")
    to_status: str
    allowed_resolutions: list[Resolution] | None = Field(
        description="Only for done targets; null = all resolutions"
    )
    rules: list[RuleOut]


class WorkflowOut(Output):
    type: TicketType
    statuses: list[StatusOut]
    transitions: list[TransitionOut]


class ProjectTemplateOut(Output):
    id: str
    name: str
    mode: TemplateMode
    version: int = Field(description="Latest template version")
    applied_version: int | None = Field(description="Version this project has")


class ProjectSettingsPut(Input):
    blocked_policy: BlockedPolicy


class ProjectDetail(ProjectOut):
    areas: list[AreaOut]
    milestones: list[MilestoneOut]
    workflows: list[WorkflowOut]
    members: list[MemberOut]
    custom_fields: list[CustomFieldOut]
    template: ProjectTemplateOut | None
    blocked_policy: BlockedPolicy
    suggested_tags: list[str]
    permissions: list[str] = Field(
        default_factory=list, description="What you may do here, from the permission matrix"
    )


class MilestoneRecapOut(Output):
    """A milestone's numbers, for the celebration card when its last ticket is done."""

    milestone: str
    project_key: str
    project_name: str
    target_date: date | None
    complete: bool = Field(description="Every ticket is done (and there is at least one)")
    on_time: bool | None = Field(description="Finished by the target date; null if unknown")
    tickets: int
    done: int
    tasks: int
    bugs: int
    ideas: int = Field(description="Drafts: ideas captured along the way")
    minutes_logged: int
    comments: int
    humans: int
    agents: int
    people: list[UserRef] = Field(description="Up to 8 people who worked on it")
    started_at: UtcDatetime | None
    finished_at: UtcDatetime | None
    days: int | None
