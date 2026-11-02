"""Rename the seeded rows to Gumball Factory

Revision ID: 0066
Revises: 0065
Create Date: 2026-11-01

ADR 0046: the system user and the default template were seeded as "Radicle" and
"Radicle default". Rows an admin already renamed are left alone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0066"
down_revision: str | None = "0065"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENAMES = (
    (
        "users",
        "display_name",
        "kind = 'system' AND handle = 'system'",
        "Radicle",
        "Gumball Factory",
    ),
    ("templates", "name", "true", "Radicle default", "Gumball Factory default"),
)


def _rename(old_index: int, new_index: int) -> None:
    for row in RENAMES:
        table, column, where = row[0], row[1], row[2]
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = :new WHERE {column} = :old AND {where}"  # noqa: S608
            ).bindparams(old=row[old_index], new=row[new_index])
        )


def upgrade() -> None:
    _rename(3, 4)


def downgrade() -> None:
    _rename(4, 3)
