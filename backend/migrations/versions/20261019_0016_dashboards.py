"""dashboards with widgets; a Summary dashboard per project

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-19
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_USER = "00000000-0000-0000-0000-000000000001"


def summary_widgets(key: str) -> list[tuple[str, str, dict[str, object], dict[str, int]]]:
    """Same as services.dashboards.SUMMARY, frozen here."""
    base = f"project = {key}"
    return [
        (
            "count",
            "Open tickets",
            {"rql": f"{base} AND category != done"},
            {"x": 0, "y": 0, "w": 3, "h": 3},
        ),
        (
            "count",
            "Blocked",
            {"rql": f"{base} AND blocked = true AND category != done"},
            {"x": 3, "y": 0, "w": 3, "h": 3},
        ),
        (
            "created_vs_resolved",
            "Created vs resolved",
            {"rql": base, "days": 30},
            {"x": 6, "y": 0, "w": 6, "h": 6},
        ),
        (
            "distribution",
            "Open by area",
            {"rql": f"{base} AND category != done", "field": "area", "chart": "bar"},
            {"x": 0, "y": 3, "w": 6, "h": 6},
        ),
        ("blocked_tickets", "Blocked tickets", {"rql": base}, {"x": 0, "y": 9, "w": 6, "h": 5}),
        ("my_tickets", "My tickets", {}, {"x": 6, "y": 6, "w": 6, "h": 5}),
    ]


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "visibility",
            postgresql.ENUM(name="filter_visibility", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("is_project_default", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "uq_dashboards_project_default",
        "dashboards",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("is_project_default"),
    )
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "dashboard_id",
            sa.Uuid(),
            sa.ForeignKey("dashboards.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("widget_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("layout", postgresql.JSONB(), nullable=False),
    )
    conn = op.get_bind()
    for project_id, key in conn.execute(sa.text("SELECT id, key FROM projects")).all():
        dashboard_id = conn.execute(
            sa.text(
                "INSERT INTO dashboards (id, owner_id, name, visibility, project_id, "
                "is_project_default) VALUES (gen_random_uuid(), CAST(:owner AS uuid), 'Summary', "
                "'project', :project, true) RETURNING id"
            ),
            {"owner": SYSTEM_USER, "project": project_id},
        ).scalar_one()
        for kind, title, config, layout in summary_widgets(key):
            conn.execute(
                sa.text(
                    "INSERT INTO dashboard_widgets (id, dashboard_id, widget_type, title, config, "
                    "layout) VALUES (gen_random_uuid(), :dashboard, :kind, :title, "
                    "CAST(:config AS jsonb), CAST(:layout AS jsonb))"
                ),
                {
                    "dashboard": dashboard_id,
                    "kind": kind,
                    "title": title,
                    "config": json.dumps(config),
                    "layout": json.dumps(layout),
                },
            )


def downgrade() -> None:
    op.drop_table("dashboard_widgets")
    op.drop_index("uq_dashboards_project_default", table_name="dashboards")
    op.drop_table("dashboards")
