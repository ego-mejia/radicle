"""Events and notifications in platform: outbox, deliveries, notifications, preferences

Revision ID: 0040
Revises: 0039
Create Date: 2026-10-21

Folio 2.1 (ADR 0038). Also users.timezone and users.digest_hour for the daily digest.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

channel = postgresql.ENUM("in_app", "email", name="notification_channel", create_type=False)
status = postgresql.ENUM(
    "pending", "sent", "failed", "skipped", name="delivery_status", create_type=False
)


def _user(name: str, ondelete: str, nullable: bool = False) -> sa.Column[object]:
    return sa.Column(
        name, sa.Uuid(), sa.ForeignKey("users.id", ondelete=ondelete), nullable=nullable
    )


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    channel.create(op.get_bind())
    status.create(op.get_bind())
    op.add_column("users", sa.Column("timezone", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("digest_hour", sa.SmallInteger(), nullable=True))
    op.create_table(
        "events_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("app", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        _user("actor_id", "SET NULL", nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        _now("occurred_at"),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_events_outbox_pending",
        "events_outbox",
        ["id"],
        postgresql_where=sa.text("dispatched_at IS NULL"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _user("user_id", "CASCADE"),
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.ForeignKey("events_outbox.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("app", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("link", sa.Text(), nullable=True),
        _user("actor_id", "SET NULL", nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        _now("created_at"),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id", "created_at"])
    op.create_table(
        "event_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.ForeignKey("events_outbox.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _user("user_id", "CASCADE"),
        sa.Column("channel", channel, nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("attempts", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        _now("created_at"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", "user_id", "channel"),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _user("user_id", "CASCADE"),
        sa.Column("app", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("channel", channel, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "app", "type", "channel"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("event_deliveries")
    op.drop_table("notifications")
    op.drop_table("events_outbox")
    op.drop_column("users", "digest_hour")
    op.drop_column("users", "timezone")
    status.drop(op.get_bind())
    channel.drop(op.get_bind())
