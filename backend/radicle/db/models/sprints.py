import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.base import Base, utcnow
from radicle.db.models.projects import _enum


class SprintState(enum.StrEnum):
    future = "future"
    active = "active"
    closed = "closed"


sprint_state_enum = _enum(SprintState, "sprint_state")


class Sprint(Base):
    __tablename__ = "sprints"
    __table_args__ = (
        Index(
            "uq_sprints_one_active_per_board",
            "board_id",
            unique=True,
            postgresql_where=text("state = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    state: Mapped[SprintState] = mapped_column(sprint_state_enum, default=SprintState.future)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    capacity_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Marked by hand in the sprint report.
    goal_met: Mapped[bool | None] = mapped_column(Boolean)
    # Saved when the sprint closes, so the report does not change afterwards.
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class SprintTicket(Base):
    """A ticket's stay in a sprint. Removing it sets `removed_at`; adding it again is a new row."""

    __tablename__ = "sprint_tickets"
    __table_args__ = (
        # A ticket is in at most one sprint that is not closed.
        Index(
            "uq_sprint_tickets_one_open",
            "ticket_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL AND NOT sprint_closed"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sprints.id", ondelete="CASCADE"), index=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    added_after_start: Mapped[bool] = mapped_column(Boolean, default=False)
    # Copy of sprints.state = closed, so the unique index above can see it.
    sprint_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class SprintCommitment(Base):
    """What the team committed to when the sprint started."""

    __tablename__ = "sprint_commitments"

    sprint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sprints.id", ondelete="CASCADE"), primary_key=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    estimate_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    remaining_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
