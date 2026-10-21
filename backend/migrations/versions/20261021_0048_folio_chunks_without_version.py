"""Folio chunks without a version: whiteboards are indexed as they are drawn

Revision ID: 0048
Revises: 0047
Create Date: 2026-10-21

Folio phase 3 (3.5). A whiteboard is never published, so its chunks have no version.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("folio_chunks", "version_id", nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM folio_chunks WHERE version_id IS NULL")
    op.alter_column("folio_chunks", "version_id", nullable=False)
