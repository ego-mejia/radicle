"""Folio public links

Revision ID: 0057
Revises: 0056
Create Date: 2026-10-21

Folio phase 5 (5.1). A read-only, revocable link to a page or a space, opened without an
account.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0057"
down_revision: str | None = "0056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

target = postgresql.ENUM("node", "space", name="folio_public_target", create_type=False)


def upgrade() -> None:
    target.create(op.get_bind())
    op.create_table(
        "folio_public_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("target_type", target, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("noindex", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.create_index("ux_folio_public_links_token", "folio_public_links", ["token"], unique=True)
    op.create_index(
        "ix_folio_public_links_target", "folio_public_links", ["target_type", "target_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_folio_public_links_target", table_name="folio_public_links")
    op.drop_index("ux_folio_public_links_token", table_name="folio_public_links")
    op.drop_table("folio_public_links")
    target.drop(op.get_bind())
