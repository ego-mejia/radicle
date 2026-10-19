from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

from radicle.db.models import UserKind
from radicle.services.auth import IssuedToken


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- system -------------------------------------------------------------------------------


class Health(BaseModel):
    status: str
    database: str


class Version(BaseModel):
    version: str
    api_version: str


class SetupStatus(BaseModel):
    needs_setup: bool


class SetupIn(Input):
    handle: str
    display_name: str
    email: EmailStr
    password: str = Field(repr=False)


# --- users --------------------------------------------------------------------------------


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    handle: str
    display_name: str
    kind: UserKind
    email: str | None
    is_instance_admin: bool
    is_active: bool
    created_at: UtcDatetime


class MeProject(BaseModel):
    key: str
    name: str
    role: str


class MeOut(UserOut):
    projects: list[MeProject] = []


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


class TokenOut(BaseModel):
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


class AgentCreated(BaseModel):
    agent: UserOut
    token: TokenCreated
    mcp_url: str
