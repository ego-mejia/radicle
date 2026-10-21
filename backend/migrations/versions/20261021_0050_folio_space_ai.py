"""Folio spaces can turn the editor AI off

Revision ID: 0050
Revises: 0049
Create Date: 2026-10-21

Folio phase 4 (4.6). Without a provider or with AI off in the space, the editor shows no AI.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "folio_spaces",
        sa.Column("ai_enabled", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("folio_spaces", "ai_enabled")
