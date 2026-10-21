"""Folio nodes: live docs, quality status, verification and archiving

Revision ID: 0041
Revises: 0040
Create Date: 2026-10-21

Folio phase 2 (2.5, 2.6, 2.7): `kind` gains live_doc; nodes gain status, verified_by,
verified_until, archived_at and archived_by; spaces gain verify_days. Nodes already
published start as published.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

status = postgresql.ENUM(
    "draft",
    "published",
    "in_review",
    "verified",
    "outdated",
    name="folio_node_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("ALTER TYPE folio_node_kind ADD VALUE IF NOT EXISTS 'live_doc'")
    status.create(op.get_bind())
    op.add_column(
        "folio_nodes", sa.Column("status", status, server_default="draft", nullable=False)
    )
    op.execute("UPDATE folio_nodes SET status = 'published' WHERE published_version_id IS NOT NULL")
    op.add_column(
        "folio_nodes",
        sa.Column(
            "verified_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.add_column("folio_nodes", sa.Column("verified_until", sa.Date(), nullable=True))
    op.add_column(
        "folio_nodes", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "folio_nodes",
        sa.Column(
            "archived_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.add_column(
        "folio_spaces",
        sa.Column("verify_days", sa.BigInteger(), server_default="90", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("folio_spaces", "verify_days")
    op.drop_column("folio_nodes", "archived_by")
    op.drop_column("folio_nodes", "archived_at")
    op.drop_column("folio_nodes", "verified_until")
    op.drop_column("folio_nodes", "verified_by")
    op.drop_column("folio_nodes", "status")
    status.drop(op.get_bind())
    # Postgres cannot drop an enum value: live docs go, then the type is rebuilt.
    op.execute("DELETE FROM folio_nodes WHERE kind = 'live_doc'")
    op.execute("ALTER TYPE folio_node_kind RENAME TO folio_node_kind_old")
    op.execute("CREATE TYPE folio_node_kind AS ENUM ('page', 'folder', 'blog_post')")
    op.execute(
        "ALTER TABLE folio_nodes ALTER COLUMN kind TYPE folio_node_kind "
        "USING kind::text::folio_node_kind"
    )
    op.execute("DROP TYPE folio_node_kind_old")
