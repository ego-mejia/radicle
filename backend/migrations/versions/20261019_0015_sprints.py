"""sprints, their tickets and commitments

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM("future", "active", "closed", name="sprint_state").create(op.get_bind())
    op.create_table(
        "sprints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "board_id",
            sa.Uuid(),
            sa.ForeignKey("boards.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("state", postgresql.ENUM(name="sprint_state", create_type=False), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("capacity_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("goal_met", sa.Boolean(), nullable=True),
        sa.Column("report", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "uq_sprints_one_active_per_board",
        "sprints",
        ["board_id"],
        unique=True,
        postgresql_where=sa.text("state = 'active'"),
    )
    op.create_table(
        "sprint_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "sprint_id",
            sa.Uuid(),
            sa.ForeignKey("sprints.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("added_after_start", sa.Boolean(), nullable=False),
        sa.Column("sprint_closed", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "uq_sprint_tickets_one_open",
        "sprint_tickets",
        ["ticket_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL AND NOT sprint_closed"),
    )
    op.create_table(
        "sprint_commitments",
        sa.Column(
            "sprint_id",
            sa.Uuid(),
            sa.ForeignKey("sprints.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("estimate_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("remaining_hours", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sprint_commitments")
    op.drop_index("uq_sprint_tickets_one_open", table_name="sprint_tickets")
    op.drop_table("sprint_tickets")
    op.drop_index("uq_sprints_one_active_per_board", table_name="sprints")
    op.drop_table("sprints")
    postgresql.ENUM(name="sprint_state").drop(op.get_bind())
