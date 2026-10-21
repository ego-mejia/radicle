import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.db.models.projects import StatusCategory, status_category_enum
from radicle.platform.db.models.base import Base


class TicketStatusPeriod(Base):
    """One stretch of time a ticket spent in one status. Open period: exited_at is null."""

    __tablename__ = "ticket_status_periods"
    __table_args__ = (
        Index("ix_status_periods_ticket", "ticket_id", "entered_at"),
        Index("ix_status_periods_status", "status_id", "entered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    # Null only for history rebuilt from a status that no longer exists.
    status_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("statuses.id", ondelete="SET NULL")
    )
    category: Mapped[StatusCategory] = mapped_column(status_category_enum)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DailyStatusCount(Base):
    """Tickets per status at the end of each day, for fast reports (cumulative flow)."""

    __tablename__ = "daily_status_counts"
    __table_args__ = (
        PrimaryKeyConstraint(
            "date", "project_id", "status_id", "milestone_key", "sprint_key", name="pk_daily_counts"
        ),
    )

    date: Mapped[date] = mapped_column(Date)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statuses.id", ondelete="CASCADE"))
    # Nullable foreign ids cannot be in a primary key, so the key uses a zero uuid for none.
    milestone_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    sprint_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ticket_count: Mapped[int] = mapped_column(Integer)
    remaining_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
