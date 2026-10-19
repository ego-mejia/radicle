"""transition rules and time spent

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM("condition", "validator", "post_function", name="rule_kind").create(
        op.get_bind()
    )
    op.create_table(
        "transition_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transition_id",
            sa.Uuid(),
            sa.ForeignKey("transitions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", postgresql.ENUM(name="rule_kind", create_type=False), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.add_column(
        "tickets",
        sa.Column("time_spent_minutes", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tickets", "time_spent_minutes")
    op.drop_table("transition_rules")
    postgresql.ENUM(name="rule_kind").drop(op.get_bind())
