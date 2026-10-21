"""Events and notifications (ADR 0038): a transactional outbox, its deliveries per user and
channel, in-app notifications and each user's preferences."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from radicle.platform.db.models.base import Base, _enum


class Channel(enum.StrEnum):
    in_app = "in_app"
    email = "email"


class DeliveryStatus(enum.StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"  # turned off in the user's preferences


class OutboxEvent(Base):
    """Written in the same transaction as the change; dispatched later by the worker."""

    __tablename__ = "events_outbox"
    __table_args__ = (
        Index(
            "ix_events_outbox_pending",
            "id",
            postgresql_where="dispatched_at IS NULL",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    app: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)


class Notification(Base):
    """An in-app notification."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    event_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("events_outbox.id", ondelete="SET NULL")
    )
    app: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    link: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventDelivery(Base):
    """One per event, user and channel: the unique key keeps a repeated dispatch from
    notifying twice."""

    __tablename__ = "event_deliveries"
    __table_args__ = (UniqueConstraint("event_id", "user_id", "channel"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("events_outbox.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    channel: Mapped[Channel] = mapped_column(_enum(Channel, "notification_channel"))
    status: Mapped[DeliveryStatus] = mapped_column(
        _enum(DeliveryStatus, "delivery_status"), default=DeliveryStatus.pending
    )
    reason: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base):
    """A user's choice for one notification type and channel; no row means the default."""

    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "app", "type", "channel"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    app: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    channel: Mapped[Channel] = mapped_column(_enum(Channel, "notification_channel"))
    enabled: Mapped[bool] = mapped_column(Boolean)
