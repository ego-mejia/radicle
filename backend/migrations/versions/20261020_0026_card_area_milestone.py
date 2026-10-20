"""Board cards show their area, milestone and subticket count

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-20

New card fields: area, milestone and children. Every existing board turns them on, at
the front, so cards show them right away; a board can still turn them off.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = ("area", "milestone", "children")


def upgrade() -> None:
    add = sa.text(
        "UPDATE boards SET card_fields = array_prepend(CAST(:name AS text), card_fields) "
        "WHERE NOT (CAST(:name AS text) = ANY(card_fields))"
    )
    for name in reversed(NEW):
        op.get_bind().execute(add, {"name": name})


def downgrade() -> None:
    remove = sa.text(
        "UPDATE boards SET card_fields = array_remove(card_fields, CAST(:name AS text))"
    )
    for name in NEW:
        op.get_bind().execute(remove, {"name": name})
