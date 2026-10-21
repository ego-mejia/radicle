"""Webhooks and their deliveries

Revision ID: 0058
Revises: 0057
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status = postgresql.ENUM(
    "pending", "sent", "failed", "skipped", name="delivery_status", create_type=False
)


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _fk(
    name: str, kind: sa.types.TypeEngine[object], target: str, ondelete: str, nullable: bool = True
) -> sa.Column[object]:
    return sa.Column(name, kind, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column(
            "events", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column(
            "filter",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        _fk("created_by", sa.Uuid(), "users.id", "SET NULL"),
        _now("created_at"),
    )
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _fk("webhook_id", sa.Uuid(), "webhooks.id", "CASCADE", nullable=False),
        _fk("event_id", sa.BigInteger(), "events_outbox.id", "SET NULL"),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        _now("created_at"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("webhook_id", "event_id", "event"),
    )
    op.create_index(
        "ix_webhook_deliveries_webhook", "webhook_deliveries", ["webhook_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_webhook", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
