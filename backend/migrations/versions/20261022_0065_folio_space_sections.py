"""Folio space sections

Revision ID: 0065
Revises: 0064
Create Date: 2026-10-22

Each space shows its pages by section (Specs, Decisions, Guides, Docs). The space admin
may hide or reorder them; null keeps the default order with every section shown.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0065"
down_revision: str | None = "0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("folio_spaces", sa.Column("sections", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("folio_spaces", "sections")
