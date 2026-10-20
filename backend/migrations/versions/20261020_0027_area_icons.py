"""Areas get an optional icon

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-20

The icon is a name from the web app's icon set, drawn in the area's color.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("areas", sa.Column("icon", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("areas", "icon")
