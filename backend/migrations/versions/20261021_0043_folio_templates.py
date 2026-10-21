"""Folio templates: page and space templates, global or per space

Revision ID: 0043
Revises: 0042
Create Date: 2026-10-21

Folio phase 3 (3.1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

kind = postgresql.ENUM("page", "space", name="folio_template_kind", create_type=False)
scope = postgresql.ENUM("global", "space", name="folio_template_scope", create_type=False)


def upgrade() -> None:
    kind.create(op.get_bind())
    scope.create(op.get_bind())
    op.create_table(
        "folio_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", kind, nullable=False),
        sa.Column("scope", scope, nullable=False),
        sa.Column(
            "space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("builtin_key", sa.Text(), nullable=True, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("doc_type_key", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column("default_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("structure", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("folio_templates")
    scope.drop(op.get_bind())
    kind.drop(op.get_bind())
