"""Slack and Teams integrations, their users and the notices they post

Revision ID: 0060
Revises: 0059
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060"
down_revision: str | None = "0059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

kind = postgresql.ENUM("slack", "teams", name="integration_kind", create_type=False)
status = postgresql.ENUM(
    "pending", "sent", "failed", "skipped", name="delivery_status", create_type=False
)


def _fk(
    name: str, kind: sa.types.TypeEngine[object], target: str, ondelete: str, nullable: bool = True
) -> sa.Column[object]:
    return sa.Column(name, kind, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    kind.create(op.get_bind())
    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", kind, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        _fk("created_by", sa.Uuid(), "users.id", "SET NULL"),
        _now("created_at"),
    )
    op.create_table(
        "integration_identities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _fk("integration_id", sa.Uuid(), "integrations.id", "CASCADE", nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        _fk("user_id", sa.Uuid(), "users.id", "CASCADE", nullable=False),
        _now("created_at"),
        sa.UniqueConstraint("integration_id", "external_id"),
    )
    op.create_table(
        "integration_notices",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _fk("integration_id", sa.Uuid(), "integrations.id", "CASCADE", nullable=False),
        _fk("event_id", sa.BigInteger(), "events_outbox.id", "SET NULL"),
        sa.Column("route", sa.Integer(), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        _now("created_at"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("integration_id", "event_id", "route"),
    )


def downgrade() -> None:
    op.drop_table("integration_notices")
    op.drop_table("integration_identities")
    op.drop_table("integrations")
    kind.drop(op.get_bind())
