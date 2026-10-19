"""configurable boards with quick filters; a Main board per project

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-19
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same as the stage 1 board: one column per status category.
MAIN_COLUMNS = [
    {"name": "To Do", "categories": ["todo"], "status_ids": [], "wip_limit": None},
    {"name": "In Progress", "categories": ["in_progress"], "status_ids": [], "wip_limit": None},
    {"name": "Done", "categories": ["done"], "status_ids": [], "wip_limit": None},
]
QUICK_FILTERS = [
    ("My tickets", "assignee = currentUser()"),
    ("Only bugs", "type = bug"),
    ("#backlog", "#backlog"),
    ("Blocked", "blocked = true"),
]


def upgrade() -> None:
    for name, values in (
        ("board_kind", ("kanban", "scrum")),
        ("wip_mode", ("soft", "hard")),
        ("swimlane", ("none", "area", "assignee", "priority", "milestone", "parent", "type")),
    ):
        postgresql.ENUM(*values, name=name).create(op.get_bind())
    op.create_table(
        "boards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", postgresql.ENUM(name="board_kind", create_type=False), nullable=False),
        sa.Column("source_rql", sa.Text(), nullable=False),
        sa.Column("columns", postgresql.JSONB(), nullable=False),
        sa.Column("wip_mode", postgresql.ENUM(name="wip_mode", create_type=False), nullable=False),
        sa.Column(
            "swimlane_by", postgresql.ENUM(name="swimlane", create_type=False), nullable=False
        ),
        sa.Column("card_fields", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("done_window_days", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "board_quick_filters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "board_id",
            sa.Uuid(),
            sa.ForeignKey("boards.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("rql", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    conn = op.get_bind()
    for project_id, key in conn.execute(sa.text("SELECT id, key FROM projects")).all():
        board_id = conn.execute(
            sa.text(
                "INSERT INTO boards (id, project_id, name, kind, source_rql, columns, wip_mode, "
                "swimlane_by, card_fields, done_window_days) VALUES (gen_random_uuid(), :project, "
                "'Main', 'kanban', :rql, CAST(:columns AS jsonb), 'soft', 'none', "
                "ARRAY['priority','assignee','tags','checklist']::text[], 14) RETURNING id"
            ),
            {"project": project_id, "rql": f"project = {key}", "columns": json.dumps(MAIN_COLUMNS)},
        ).scalar_one()
        for position, (name, rql) in enumerate(QUICK_FILTERS):
            conn.execute(
                sa.text(
                    "INSERT INTO board_quick_filters (id, board_id, name, rql, position) "
                    "VALUES (gen_random_uuid(), :board, :name, :rql, :position)"
                ),
                {"board": board_id, "name": name, "rql": rql, "position": position},
            )


def downgrade() -> None:
    op.drop_table("board_quick_filters")
    op.drop_table("boards")
    for name in ("swimlane", "wip_mode", "board_kind"):
        postgresql.ENUM(name=name).drop(op.get_bind())
