from datetime import date
from uuid import UUID

from pydantic import ConfigDict, Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.api.schemas.fields import CustomFieldOut
from radicle.db.models import (
    BlockedPolicy,
    MilestoneStatus,
    ProjectRole,
    Resolution,
    StatusCategory,
    TemplateMode,
    TicketType,
    UserKind,
)


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


class AreaOut(Output):
    model_config = ConfigDict(from_attributes=True)

    name: str
    color: str | None
    position: int
    archived: bool


class AreaCreate(Input):
    name: str
    color: str | None = None


class AreaPatch(Input):
    name: str | None = None
    color: str | None = Field(default=None, description="Hex like #4D7C0F; null clears it")
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
    role: ProjectRole
    is_active: bool


class MemberPut(Input):
    role: ProjectRole


class StatusOut(Output):
    ref: str | None = Field(description="Stable slug; renames keep it")
    name: str
    category: StatusCategory
    is_initial: bool


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
