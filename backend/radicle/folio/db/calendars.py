"""Folio calendars (phase 5.8): a space's calendars and their events. A calendar may also
show the milestones of Docket projects, read through `docket.public`, and has a token for
its read-only iCal feed."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum, utcnow


class EventCategory(enum.StrEnum):
    vacation = "vacation"
    release = "release"
    event = "event"
    oncall = "oncall"
    other = "other"


class FolioCalendar(Base):
    __tablename__ = "folio_calendars"
    __table_args__ = (Index("ux_folio_calendars_ical_token", "ical_token", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_spaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(Text, default="blue", server_default="blue")
    # Keys of the Docket projects whose milestones it shows; empty shows none.
    docket_projects: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    ical_token: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class FolioEvent(Base):
    __tablename__ = "folio_events"
    __table_args__ = (Index("ix_folio_events_calendar_start", "calendar_id", "start_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folio_calendars.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    category: Mapped[EventCategory] = mapped_column(
        _enum(EventCategory, "folio_event_category"), default=EventCategory.event
    )
    people: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default="{}"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
