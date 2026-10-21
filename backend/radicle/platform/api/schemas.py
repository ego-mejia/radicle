from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]
Date = date


class Output(BaseModel):
    """Response models: fields with defaults are always present, so the schema marks them
    required and generated clients do not treat them as optional."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class Page[T](Output):
    items: list[T]
    next_cursor: str | None = None


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Warning(BaseModel):
    code: str
    message: str | None = None
    by: list[str] | None = None
