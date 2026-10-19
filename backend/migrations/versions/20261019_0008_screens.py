"""screens

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM("create", "edit", "transition", name="screen_operation").create(op.get_bind())
    op.create_table(
        "screens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ticket_type", postgresql.ENUM(name="ticket_type", create_type=False), nullable=False
        ),
        sa.Column(
            "operation", postgresql.ENUM(name="screen_operation", create_type=False), nullable=False
        ),
        sa.Column(
            "transition_id",
            sa.Uuid(),
            sa.ForeignKey("transitions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("fields", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_table("screens")
    postgresql.ENUM(name="screen_operation").drop(op.get_bind())
