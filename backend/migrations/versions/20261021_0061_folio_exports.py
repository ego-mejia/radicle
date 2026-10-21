"""Folio exports

Revision ID: 0061
Revises: 0060
Create Date: 2026-10-21

Folio phase 5 (5.2). A page or space written to PDF, Word, HTML or Markdown by the worker.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0061"
down_revision: str | None = "0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

fmt = postgresql.ENUM(
    "pdf", "docx", "html", "markdown", name="folio_export_format", create_type=False
)
scope = postgresql.ENUM("node", "space", name="folio_export_scope", create_type=False)
status = postgresql.ENUM(
    "queued", "running", "done", "failed", name="folio_export_status", create_type=False
)


def upgrade() -> None:
    for enum in (fmt, scope, status):
        enum.create(op.get_bind())
    op.create_table(
        "folio_exports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("format", fmt, nullable=False),
        sa.Column("scope", scope, nullable=False),
        sa.Column(
            "space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_id", sa.Uuid(), sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("options", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("stats", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("file_key", sa.Text(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_folio_exports_created_by", "folio_exports", ["created_by", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_folio_exports_created_by", table_name="folio_exports")
    op.drop_table("folio_exports")
    for enum in (status, scope, fmt):
        enum.drop(op.get_bind())
