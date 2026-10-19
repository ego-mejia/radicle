from typing import Any

from pydantic import Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.db.models import CustomFieldType, TicketType


class FieldOption(Input):
    value: str
    label: str | None = None
    color: str | None = Field(default=None, description="Hex like #4D7C0F")


class FieldOptionOut(Output):
    value: str
    label: str
    color: str | None


class CustomFieldOut(Output):
    key: str = Field(description="Use it as cf.<key> in RQL and in custom_fields")
    name: str
    field_type: CustomFieldType
    options: list[FieldOptionOut]
    applies_to_types: list[TicketType]
    applies_to_areas: list[str] | None = Field(description="null = every area")
    position: int
    archived: bool
    from_template: bool
    created_at: UtcDatetime


class CustomFieldCreate(Input):
    key: str = Field(description="2-40 chars: lowercase letter, then letters, digits or _")
    name: str
    field_type: CustomFieldType
    options: list[FieldOption] | None = Field(default=None, description="Only for select")
    applies_to_types: list[TicketType] | None = Field(default=None, description="null = all")
    applies_to_areas: list[str] | None = Field(default=None, description="Area names; null = all")


class CustomFieldPatch(Input):
    """Key and type never change. Changing options keeps the values tickets already have."""

    name: str | None = None
    options: list[FieldOption] | None = None
    applies_to_types: list[TicketType] | None = None
    applies_to_areas: list[str] | None = Field(default=None, description="null = every area")
    position: int | None = None
    archived: bool | None = None


def option_dicts(options: list[FieldOption] | None) -> list[dict[str, Any]] | None:
    return [o.model_dump() for o in options] if options is not None else None
