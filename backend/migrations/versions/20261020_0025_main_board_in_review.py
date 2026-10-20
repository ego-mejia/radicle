"""Main boards still on the three default columns get an In Review column

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-20

The default Main board had To Do | In Progress | Done by category, so In Review and QA
Verified hid inside In Progress and cards could not be dragged between them. Boards that
nobody reconfigured get To Do | In Progress | In Review | Done; In Review names the
in-progress statuses after the first one of each ticket type, and any called *review*.
"""

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = [
    {"name": "To Do", "categories": ["todo"], "status_ids": [], "wip_limit": None},
    {"name": "In Progress", "categories": ["in_progress"], "status_ids": [], "wip_limit": None},
    {"name": "Done", "categories": ["done"], "status_ids": [], "wip_limit": None},
]


def _normal(columns: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": c.get("name"),
            "categories": sorted(c.get("categories") or []),
            "status_ids": sorted(c.get("status_ids") or []),
            "wip_limit": c.get("wip_limit"),
        }
        for c in columns or []
    ]


def _review_ids(bind: sa.Connection, project_id: Any) -> list[str]:
    rows = bind.execute(
        sa.text(
            "SELECT id, ticket_type::text, name FROM statuses "
            "WHERE project_id = :p AND category = 'in_progress' ORDER BY ticket_type, position"
        ),
        {"p": project_id},
    ).all()
    seen: set[str] = set()
    review: list[str] = []
    for status_id, ticket_type, name in rows:
        if ticket_type in seen or "review" in name.lower():
            review.append(str(status_id))
        seen.add(ticket_type)
    return review


def _new(review: list[str]) -> list[dict[str, Any]]:
    columns = [dict(c) for c in OLD]
    columns.insert(
        2, {"name": "In Review", "categories": [], "status_ids": review, "wip_limit": None}
    )
    return columns


def _boards(bind: sa.Connection) -> list[Any]:
    return list(
        bind.execute(sa.text("SELECT id, project_id, columns FROM boards WHERE name = 'Main'"))
    )


def _save(bind: sa.Connection, board_id: Any, columns: list[dict[str, Any]]) -> None:
    bind.execute(
        sa.text("UPDATE boards SET columns = CAST(:c AS jsonb) WHERE id = :id"),
        {"c": json.dumps(columns), "id": board_id},
    )


def upgrade() -> None:
    bind = op.get_bind()
    for board_id, project_id, columns in _boards(bind):
        if _normal(columns) != _normal(OLD):
            continue  # someone configured it: leave it as they want it
        review = _review_ids(bind, project_id)
        if review:
            _save(bind, board_id, _new(review))


def downgrade() -> None:
    bind = op.get_bind()
    for board_id, project_id, columns in _boards(bind):
        review = _review_ids(bind, project_id)
        if review and _normal(columns) == _normal(_new(review)):
            _save(bind, board_id, [dict(c) for c in OLD])
