"""Folio whiteboards: kind whiteboard and the scene each one holds

Revision ID: 0047
Revises: 0046
Create Date: 2026-10-21

Folio phase 3 (3.5).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE folio_node_kind ADD VALUE IF NOT EXISTS 'whiteboard'")
    op.create_table(
        "folio_whiteboards",
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("folio_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("elements", postgresql.JSONB(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("folio_whiteboards")
    # Postgres cannot drop an enum value: whiteboards go, then the type is rebuilt.
    op.execute("DELETE FROM folio_nodes WHERE kind = 'whiteboard'")
    op.execute("ALTER TYPE folio_node_kind RENAME TO folio_node_kind_old")
    op.execute(
        "CREATE TYPE folio_node_kind AS ENUM "
        "('page', 'folder', 'blog_post', 'live_doc', 'database')"
    )
    op.execute(
        "ALTER TABLE folio_nodes ALTER COLUMN kind TYPE folio_node_kind "
        "USING kind::text::folio_node_kind"
    )
    op.execute("DROP TYPE folio_node_kind_old")
