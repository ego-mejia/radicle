"""Folio databases: kind database, their columns and views, and their rows

Revision ID: 0045
Revises: 0044
Create Date: 2026-10-21

Folio phase 3 (3.6).
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
    op.execute("ALTER TYPE folio_node_kind ADD VALUE IF NOT EXISTS 'database'")
    op.create_table(
        "folio_databases",
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("columns", postgresql.JSONB(), nullable=False),
        sa.Column("views", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "folio_db_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("values", postgresql.JSONB(), nullable=False),
        sa.Column("rank", sa.Text(collation="C"), nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_folio_db_rows_node_rank", "folio_db_rows", ["node_id", "rank"])


def downgrade() -> None:
    op.drop_table("folio_db_rows")
    op.drop_table("folio_databases")
    # Postgres cannot drop an enum value: databases go, then the type is rebuilt.
    op.execute("DELETE FROM folio_nodes WHERE kind = 'database'")
    op.execute("ALTER TYPE folio_node_kind RENAME TO folio_node_kind_old")
    op.execute("CREATE TYPE folio_node_kind AS ENUM ('page', 'folder', 'blog_post', 'live_doc')")
    op.execute(
        "ALTER TABLE folio_nodes ALTER COLUMN kind TYPE folio_node_kind "
        "USING kind::text::folio_node_kind"
    )
    op.execute("DROP TYPE folio_node_kind_old")
