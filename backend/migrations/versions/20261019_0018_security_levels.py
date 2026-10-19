"""security levels for restricted tickets

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_levels",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("include_participants", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "uq_security_levels_project_name",
        "security_levels",
        ["project_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "security_level_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "level_id",
            sa.Uuid(),
            sa.ForeignKey("security_levels.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "group_id",
            sa.Uuid(),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.CheckConstraint(
            "(group_id IS NULL) <> (user_id IS NULL)", name="ck_security_level_grants_one"
        ),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "security_level_id",
            sa.Uuid(),
            sa.ForeignKey("security_levels.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_tickets_security_level_id", "tickets", ["security_level_id"])


def downgrade() -> None:
    op.drop_index("ix_tickets_security_level_id", table_name="tickets")
    op.drop_column("tickets", "security_level_id")
    op.drop_table("security_level_grants")
    op.drop_index("uq_security_levels_project_name", table_name="security_levels")
    op.drop_table("security_levels")
