from pydantic import Field

from radicle.docket.api.schemas.tickets import UserRef
from radicle.docket.db.models import ProjectRole
from radicle.platform.api.schemas import Input, Output, UtcDatetime


class GroupOut(Output):
    name: str
    description: str
    member_count: int
    created_at: UtcDatetime


class GroupDetail(GroupOut):
    members: list[UserRef]


class GroupCreate(Input):
    name: str = Field(description="No spaces, e.g. equipo-legal")
    description: str = ""


class GroupPatch(Input):
    name: str | None = None
    description: str | None = None


class GroupRoleOut(Output):
    group: str
    role: ProjectRole
    member_count: int


class GroupRolePut(Input):
    role: ProjectRole


class PermissionRow(Output):
    permission: str
    description: str
    member: bool
    viewer: bool
    member_default: bool
    viewer_default: bool


class PermissionsOut(Output):
    project: str
    rows: list[PermissionRow]


class PermissionsPut(Input):
    member: dict[str, bool] = Field(default_factory=dict)
    viewer: dict[str, bool] = Field(default_factory=dict)
