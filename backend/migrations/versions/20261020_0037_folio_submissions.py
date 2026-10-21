"""Folio submissions: agents' proposed versions waiting for approval

Revision ID: 0037
Revises: 0036
Create Date: 2026-10-20

Folio 1.5.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "superseded",
    name="folio_submission_status",
    create_type=False,
)


def upgrade() -> None:
    status.create(op.get_bind())
    op.create_table(
        "folio_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_json", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Uuid(), sa.ForeignKey("folio_versions.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_folio_submissions_node_id", "folio_submissions", ["node_id"])
    op.create_index("ix_folio_submissions_status", "folio_submissions", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("folio_submissions")
    status.drop(op.get_bind())
