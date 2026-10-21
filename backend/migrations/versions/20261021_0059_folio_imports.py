"""Folio imports and external refs

Revision ID: 0059
Revises: 0058
Create Date: 2026-10-21

Folio phase 5.3: imports from Confluence, Notion, Word and Markdown, with the node each
imported page became so importing again updates it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059"
down_revision: str | None = "0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source = postgresql.ENUM(
    "confluence", "notion", "word", "markdown", name="folio_import_source", create_type=False
)
status = postgresql.ENUM(
    "uploaded",
    "checked",
    "running",
    "done",
    "failed",
    name="folio_import_status",
    create_type=False,
)


def _json(name: str) -> sa.Column[object]:
    return sa.Column(name, postgresql.JSONB(), server_default="{}", nullable=False)


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    source.create(op.get_bind())
    status.create(op.get_bind())
    op.create_table(
        "folio_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", source, nullable=False),
        sa.Column(
            "target_space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("upload_key", sa.Text(), nullable=False),
        _json("options"),
        sa.Column("status", status, nullable=False),
        _json("report"),
        _json("stats"),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        _now("created_at"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_folio_imports_created_at", "folio_imports", ["created_at"])
    op.create_table(
        "folio_external_refs",
        sa.Column("source", source, primary_key=True),
        sa.Column("external_id", sa.Text(), primary_key=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _now("created_at"),
    )
    op.create_index("ix_folio_external_refs_node_id", "folio_external_refs", ["node_id"])


def downgrade() -> None:
    op.drop_index("ix_folio_external_refs_node_id", table_name="folio_external_refs")
    op.drop_table("folio_external_refs")
    op.drop_index("ix_folio_imports_created_at", table_name="folio_imports")
    op.drop_table("folio_imports")
    status.drop(op.get_bind())
    source.drop(op.get_bind())
