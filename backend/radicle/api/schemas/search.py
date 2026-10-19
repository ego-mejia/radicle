from pydantic import Field

from radicle.api.schemas.common import Output
from radicle.api.schemas.tickets import TicketSummary


class SearchWarningOut(Output):
    code: str
    message: str
    position: int


class SearchPage(Output):
    items: list[TicketSummary]
    total: int
    next_cursor: str | None = None
    warnings: list[SearchWarningOut] = Field(default_factory=list)


class FieldInfo(Output):
    name: str
    type: str
    operators: list[str]
    supports_in: bool
    supports_empty: bool
    description: str
    values: list[str] = Field(default_factory=list)


class ProjectValues(Output):
    project: str
    statuses: list[str]
    areas: list[str]
    milestones: list[str]
    handles: list[str]
    tags: list[str] = Field(description="Most used tags first")
    custom_fields: list[FieldInfo] = Field(
        default_factory=list, description="cf.<key> fields of the project"
    )


class SearchFields(Output):
    fields: list[FieldInfo]
    sort_fields: list[str]
    functions: list[str]
    keywords: list[str]
    values: ProjectValues | None = None
