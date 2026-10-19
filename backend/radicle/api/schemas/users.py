from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.db.models import ProjectRole, UserKind
from radicle.services.auth import IssuedToken

# --- system -------------------------------------------------------------------------------


class Health(Output):
    status: str
    database: str


class Version(Output):
    version: str
    api_version: str


class SetupStatus(Output):
    needs_setup: bool


class SetupIn(Input):
    handle: str
    display_name: str
    email: EmailStr
    password: str = Field(repr=False)


# --- users --------------------------------------------------------------------------------


class UserOut(Output):
    model_config = ConfigDict(from_attributes=True)

    handle: str
    display_name: str
    kind: UserKind
    email: str | None
    is_instance_admin: bool
    is_active: bool
    auth_source: str = "local"
    created_at: UtcDatetime


class MeProject(Output):
    key: str
    name: str
    role: ProjectRole = Field(description="Effective role: direct or through a group")
    permissions: list[str] = Field(
        default_factory=list, description="What you may do there, from the permission matrix"
    )


class MeOut(UserOut):
    projects: list[MeProject] = Field(default_factory=list)


class LoginIn(Input):
    email: EmailStr
    password: str = Field(repr=False)


class MePatch(Input):
    display_name: str | None = None
    current_password: str | None = Field(default=None, repr=False)
    new_password: str | None = Field(default=None, repr=False)


class UserCreate(Input):
    handle: str
    display_name: str
    email: EmailStr
    password: str = Field(repr=False, description="Temporary password the user should change")
    is_instance_admin: bool = False


class UserPatch(Input):
    display_name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, repr=False)
    is_active: bool | None = None
    is_instance_admin: bool | None = None


class AgentCreate(Input):
    handle: str
    display_name: str
    token_name: str = "default"


# --- tokens -------------------------------------------------------------------------------


class TokenOut(Output):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    last_used_at: UtcDatetime | None
    expires_at: UtcDatetime | None
    revoked_at: UtcDatetime | None
    created_at: UtcDatetime


class TokenCreated(TokenOut):
    token: str = Field(description="Shown only once; store it now")

    @classmethod
    def from_issued(cls, issued: IssuedToken) -> "TokenCreated":
        return cls.model_validate(
            {**TokenOut.model_validate(issued.record).model_dump(), "token": issued.token}
        )


class TokenCreate(Input):
    name: str
    expires_at: datetime | None = None


class AgentCreated(Output):
    agent: UserOut
    token: TokenCreated
    mcp_url: str
