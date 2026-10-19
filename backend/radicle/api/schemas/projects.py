from datetime import date

from pydantic import ConfigDict, Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.api.schemas.fields import CustomFieldOut
from radicle.db.models import (
    MilestoneStatus,
    ProjectRole,
    Resolution,
    StatusCategory,
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
    name: str
    category: StatusCategory
    is_initial: bool


class TransitionOut(Output):
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


class ProjectDetail(ProjectOut):
    areas: list[AreaOut]
    milestones: list[MilestoneOut]
    workflows: list[WorkflowOut]
    members: list[MemberOut]
    custom_fields: list[CustomFieldOut]
