"""votes, worklogs and time tracking columns

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    postgresql.ENUM("auto", "manual", name="remaining_mode").create(op.get_bind())
    op.add_column("tickets", sa.Column("original_estimate_hours", sa.Numeric(7, 2), nullable=True))
    op.add_column("tickets", sa.Column("remaining_hours", sa.Numeric(7, 2), nullable=True))
    op.add_column(
        "tickets",
        sa.Column(
            "remaining_mode",
            postgresql.ENUM(name="remaining_mode", create_type=False),
            nullable=False,
            server_default="auto",
        ),
    )
    op.add_column(
        "tickets", sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0")
    )
    # Tickets that already had an estimate: it is their original one, nothing spent yet.
    op.execute(
        "UPDATE tickets SET original_estimate_hours = estimate_hours, "
        "remaining_hours = estimate_hours WHERE estimate_hours IS NOT NULL"
    )
    op.create_table(
        "ticket_votes",
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
        _ts("created_at"),
    )
    op.create_table(
        "worklogs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        _ts("started_at"),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("deleted_at", nullable=True),
        sa.CheckConstraint("minutes BETWEEN 1 AND 1440", name="ck_worklogs_minutes"),
    )
    op.create_index("ix_tickets_project_votes", "tickets", ["project_id", "vote_count"])


def downgrade() -> None:
    op.drop_index("ix_tickets_project_votes", table_name="tickets")
    op.drop_table("worklogs")
    op.drop_table("ticket_votes")
    for column in ("vote_count", "remaining_mode", "remaining_hours", "original_estimate_hours"):
        op.drop_column("tickets", column)
    postgresql.ENUM(name="remaining_mode").drop(op.get_bind())
