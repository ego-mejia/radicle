"""ticket key aliases for moved tickets

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_key_aliases",
        sa.Column("old_key", postgresql.CITEXT(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("ticket_key_aliases")
