"""templates, sync runs, template refs and the system user

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-19
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TEMPLATE_ID = "00000000-0000-0000-0000-000000000002"
# Frozen copy of the stage 1 workflows as a template config.
DEFAULT_CONFIG = json.loads(
    (Path(__file__).parent.parent / "sql" / "default_template_v1.json").read_text()
)


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_kind ADD VALUE IF NOT EXISTS 'system'")
    op.drop_constraint("ck_users_agent_no_credentials", "users", type_="check")
    op.create_check_constraint(
        "ck_users_agent_no_credentials",
        "users",
        "(kind::text <> 'human' AND email IS NULL AND password_hash IS NULL) "
        "OR kind::text = 'human'",
    )
    op.execute(
        sa.text(
            "INSERT INTO users (id, handle, display_name, kind, is_active) "
            "VALUES (CAST(:id AS uuid), 'system', 'Radicle', 'system', false) "
            "ON CONFLICT DO NOTHING"
        ).bindparams(id=SYSTEM_USER_ID)
    )

    for name, values in (
        ("sync_status", ("pending", "running", "succeeded", "failed")),
        ("template_mode", ("linked", "detached")),
        ("blocked_policy", ("warn", "enforce")),
    ):
        postgresql.ENUM(*values, name=name).create(op.get_bind())

    op.create_table(
        "templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("archived_at", nullable=True),
    )
    op.create_table(
        "template_sync_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="sync_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("status_mappings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("started_at", nullable=True),
        _ts("finished_at", nullable=True),
    )

    op.add_column(
        "projects",
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "template_mode", postgresql.ENUM(name="template_mode", create_type=False), nullable=True
        ),
    )
    op.add_column("projects", sa.Column("template_version", sa.Integer(), nullable=True))
    op.add_column(
        "projects",
        sa.Column(
            "blocked_policy",
            postgresql.ENUM(name="blocked_policy", create_type=False),
            nullable=False,
            server_default="warn",
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "suggested_tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"
        ),
    )
    op.add_column("statuses", sa.Column("template_ref", sa.Text(), nullable=True))
    op.add_column("transitions", sa.Column("template_ref", sa.Text(), nullable=True))

    # "Radicle default" with the stage 1 workflows; every existing project is linked to it.
    op.execute(
        sa.text(
            "INSERT INTO templates (id, name, description_md, config, version) "
            "VALUES (CAST(:id AS uuid), 'Radicle default', :description, CAST(:config AS jsonb), 1)"
        ).bindparams(
            id=DEFAULT_TEMPLATE_ID,
            description="Task, Bug and Draft workflows from stage 1.",
            config=json.dumps(DEFAULT_CONFIG),
        )
    )
    op.execute(
        sa.text(
            "UPDATE projects SET template_id = CAST(:id AS uuid), template_mode = 'linked', "
            "template_version = 1"
        ).bindparams(id=DEFAULT_TEMPLATE_ID)
    )
    for ticket_type, workflow in DEFAULT_CONFIG["workflows"].items():
        names = {s["ref"]: s["name"] for s in workflow["statuses"]}
        for ref, name in names.items():
            op.execute(
                sa.text(
                    "UPDATE statuses SET template_ref = :ref "
                    "WHERE ticket_type = CAST(:type AS ticket_type) AND name = :name"
                ).bindparams(ref=ref, type=ticket_type, name=name)
            )
        for t in workflow["transitions"]:
            from_name = names[t["from"]] if t["from"] else None
            op.execute(
                sa.text(
                    """
                    UPDATE transitions tr SET template_ref = :ref
                    WHERE tr.ticket_type = CAST(:type AS ticket_type) AND tr.name = :name
                      AND (
                        (CAST(:from_name AS text) IS NULL AND tr.from_status_id IS NULL)
                        OR tr.from_status_id IN (
                          SELECT s.id FROM statuses s
                          WHERE s.project_id = tr.project_id
                            AND s.ticket_type = CAST(:type AS ticket_type)
                            AND s.name = :from_name
                        )
                      )
                    """
                ).bindparams(ref=t["ref"], type=ticket_type, name=t["name"], from_name=from_name)
            )


def downgrade() -> None:
    op.drop_column("transitions", "template_ref")
    op.drop_column("statuses", "template_ref")
    for column in (
        "suggested_tags",
        "blocked_policy",
        "template_version",
        "template_mode",
        "template_id",
    ):
        op.drop_column("projects", column)
    op.drop_table("template_sync_runs")
    op.drop_table("templates")
    for name in ("blocked_policy", "template_mode", "sync_status"):
        postgresql.ENUM(name=name).drop(op.get_bind())

    # The history may reference the system user, so it stays as an inactive agent.
    op.execute(
        "DELETE FROM users u WHERE u.kind = 'system' "
        "AND NOT EXISTS (SELECT 1 FROM ticket_events e WHERE e.actor_id = u.id)"
    )
    op.execute("UPDATE users SET kind = 'agent' WHERE kind = 'system'")
    op.drop_constraint("ck_users_agent_no_credentials", "users", type_="check")
    op.execute("ALTER TYPE user_kind RENAME TO user_kind_old")
    op.execute("CREATE TYPE user_kind AS ENUM ('human', 'agent')")
    op.execute("ALTER TABLE users ALTER COLUMN kind TYPE user_kind USING kind::text::user_kind")
    op.execute("DROP TYPE user_kind_old")
    op.create_check_constraint(
        "ck_users_agent_no_credentials",
        "users",
        "(kind = 'agent' AND email IS NULL AND password_hash IS NULL) OR kind = 'human'",
    )
