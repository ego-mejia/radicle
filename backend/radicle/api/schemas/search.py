from pydantic import BaseModel, Field

from radicle.api.schemas.tickets import TicketSummary


class SearchWarningOut(BaseModel):
    code: str
    message: str
    position: int


class SearchPage(BaseModel):
    items: list[TicketSummary]
    total: int
    next_cursor: str | None = None
    warnings: list[SearchWarningOut] = Field(default_factory=list)


class FieldInfo(BaseModel):
    name: str
    type: str
    operators: list[str]
    supports_in: bool
    supports_empty: bool
    description: str
    values: list[str] = Field(default_factory=list)


class ProjectValues(BaseModel):
    project: str
    statuses: list[str]
    areas: list[str]
    milestones: list[str]
    handles: list[str]
    tags: list[str] = Field(description="Most used tags first")


class SearchFields(BaseModel):
    fields: list[FieldInfo]
    sort_fields: list[str]
    functions: list[str]
    keywords: list[str]
    values: ProjectValues | None = None
