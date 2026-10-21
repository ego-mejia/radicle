"""Automation rules and their runs

Revision ID: 0062
Revises: 0061
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0062"
down_revision: str | None = "0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status = postgresql.ENUM(
    "pending", "sent", "failed", "skipped", name="delivery_status", create_type=False
)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _fk(
    name: str, kind: sa.types.TypeEngine[object], target: str, ondelete: str, nullable: bool = True
) -> sa.Column[object]:
    return sa.Column(name, kind, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _texts(name: str) -> sa.Column[object]:
    return sa.Column(
        name, postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("trigger", JSONB, nullable=False),
        sa.Column("filter", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("actions", JSONB, nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        _fk("created_by", sa.Uuid(), "users.id", "SET NULL"),
        _now("created_at"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        _fk("rule_id", sa.Uuid(), "automation_rules.id", "CASCADE", nullable=False),
        _fk("event_id", sa.BigInteger(), "events_outbox.id", "SET NULL"),
        sa.Column("target", sa.Text(), server_default="", nullable=False),
        sa.Column("data", JSONB, nullable=False),
        _texts("chain"),
        sa.Column("status", status, nullable=False),
        _texts("log"),
        _now("created_at"),
        sa.UniqueConstraint("rule_id", "event_id", "target"),
    )


def downgrade() -> None:
    op.drop_table("automation_runs")
    op.drop_table("automation_rules")
