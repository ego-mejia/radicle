import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _system_clock() -> datetime:
    return datetime.now(UTC)


# Every "now" in Radicle goes through here; tests that replay a dated history swap it.
clock = _system_clock


def utcnow() -> datetime:
    return clock()


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


def _enum[E: enum.Enum](cls: type[E], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])
