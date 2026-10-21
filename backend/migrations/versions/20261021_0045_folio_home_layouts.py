"""Folio home layouts: the admin's draft and every published layout

Revision ID: 0045
Revises: 0044
Create Date: 2026-10-21

Folio phase 3 (3.2).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folio_home_layouts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("layout", postgresql.JSONB(), nullable=False),
        sa.Column("is_draft", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ux_folio_home_layouts_draft",
        "folio_home_layouts",
        ["is_draft"],
        unique=True,
        postgresql_where=sa.text("is_draft"),
    )


def downgrade() -> None:
    op.drop_table("folio_home_layouts")
