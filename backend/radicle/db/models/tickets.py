import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radicle.db.models.base import Base, utcnow
from radicle.db.models.projects import (
    Resolution,
    Status,
    TicketType,
    _enum,
    resolution_enum,
    ticket_type_enum,
)
from radicle.db.models.users import User


class Priority(enum.StrEnum):
    highest = "highest"
    high = "high"
    medium = "medium"
    low = "low"
    lowest = "lowest"


PRIORITY_ORDER = {
    Priority.lowest: 1,
    Priority.low: 2,
    Priority.medium: 3,
    Priority.high: 4,
    Priority.highest: 5,
}

priority_enum = _enum(Priority, "priority")

# Title weighs more than description; both languages so stemming works in en and es.
SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english'::regconfig, coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(description_md, '')), 'B') || "
    "setweight(to_tsvector('spanish'::regconfig, coalesce(description_md, '')), 'B')"
)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_tickets_project_number"),
        Index("ix_tickets_tags", "tags", postgresql_using="gin"),
        Index("ix_tickets_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_tickets_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("ix_tickets_project_status", "project_id", "status_id"),
        Index("ix_tickets_project_rank", "project_id", "rank"),
        Index(
            "ix_tickets_custom_fields",
            "custom_fields",
            postgresql_using="gin",
            postgresql_ops={"custom_fields": "jsonb_path_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    type: Mapped[TicketType] = mapped_column(ticket_type_enum)
    title: Mapped[str] = mapped_column(Text)
    description_md: Mapped[str] = mapped_column(Text, default="", server_default="")
    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statuses.id"))
    resolution: Mapped[Resolution | None] = mapped_column(resolution_enum)
    priority: Mapped[Priority] = mapped_column(
        priority_enum, default=Priority.medium, server_default="medium"
    )
    area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("areas.id"), index=True)
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("milestones.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tickets.id"), index=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    estimate_hours: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    rank: Mapped[str] = mapped_column(Text)
    # {"environment": "prod", "requires_signature": true}; user fields hold the user id.
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), deferred=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[Status] = relationship(lazy="joined")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id], lazy="joined")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id], lazy="joined")


class TicketCollaborator(Base):
    __tablename__ = "ticket_collaborators"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    user: Mapped[User] = relationship(lazy="joined")


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), index=True
    )
    mentioned_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class EventType(enum.StrEnum):
    created = "created"
    field_changed = "field_changed"
    status_changed = "status_changed"
    type_changed = "type_changed"
    checklist_item_toggled = "checklist_item_toggled"
    collaborator_added = "collaborator_added"
    collaborator_removed = "collaborator_removed"
    link_added = "link_added"
    link_removed = "link_removed"
    comment_added = "comment_added"
    comment_edited = "comment_edited"
    comment_deleted = "comment_deleted"
    deleted = "deleted"
    restored = "restored"
    custom_field_changed = "custom_field_changed"
    status_remapped = "status_remapped"


class TicketEvent(Base):
    """Append-only history. A database trigger rejects UPDATE, DELETE and TRUNCATE."""

    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_id_id", "ticket_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(Text)
    field: Mapped[str | None] = mapped_column(Text)
    old_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )

    actor: Mapped[User] = relationship(lazy="joined")
