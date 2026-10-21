from pydantic import Field

from radicle.platform.api.schemas import Input, Output


class SecurityLevelOut(Output):
    id: str
    name: str
    description: str
    include_participants: bool = Field(
        description="Reporter, assignee and collaborators always see their tickets"
    )
    groups: list[str]
    users: list[str]
    ticket_count: int


class SecurityLevelCreate(Input):
    name: str
    description: str = ""
    include_participants: bool = True


class SecurityLevelPatch(Input):
    name: str | None = None
    description: str | None = None
    include_participants: bool | None = None


class GrantsPut(Input):
    groups: list[str] = Field(default_factory=list, description="Group names")
    users: list[str] = Field(default_factory=list, description="Handles")
