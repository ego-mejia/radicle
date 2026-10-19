"""job queue, progress jobs and custom fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-19
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.util import await_

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copy of Procrastinate's schema for the pinned version, so this migration never
# changes when the library is upgraded. Later Procrastinate migrations get their own revision.
PROCRASTINATE_SQL = Path(__file__).parent.parent / "sql" / "procrastinate_3_10_schema.sql"

DROP_PROCRASTINATE = """
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables
           WHERE schemaname = current_schema() AND tablename LIKE 'procrastinate%' LOOP
    EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
  END LOOP;
  FOR r IN SELECT p.oid::regprocedure AS sig FROM pg_proc p
           JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = current_schema() AND p.proname LIKE 'procrastinate%' LOOP
    EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', r.sig);
  END LOOP;
  FOR r IN SELECT t.typname FROM pg_type t
           JOIN pg_namespace n ON n.oid = t.typnamespace
           WHERE n.nspname = current_schema() AND t.typname LIKE 'procrastinate%'
             AND t.typtype IN ('e', 'c') LOOP
    EXECUTE format('DROP TYPE IF EXISTS %I CASCADE', r.typname);
  END LOOP;
END $$;
"""


def _execute_script(sql: str) -> None:
    """Run a multi-statement script. asyncpg only allows that outside prepared statements,
    so it goes through the raw driver connection (inside Alembic's greenlet)."""
    driver = op.get_bind().connection.dbapi_connection.driver_connection  # type: ignore[union-attr]
    await_(driver.execute(sql))


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    _execute_script(PROCRASTINATE_SQL.read_text())

    job_status = postgresql.ENUM("pending", "running", "succeeded", "failed", name="job_status")
    job_status.create(op.get_bind())
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="job_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, index=True),
        _ts("created_at"),
        _ts("finished_at", nullable=True),
    )

    field_type = postgresql.ENUM(
        "text", "number", "date", "select", "checkbox", "user", "url", name="custom_field_type"
    )
    field_type.create(op.get_bind())
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "field_type",
            postgresql.ENUM(name="custom_field_type", create_type=False),
            nullable=False,
        ),
        sa.Column("options", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "applies_to_types",
            postgresql.ARRAY(postgresql.ENUM(name="ticket_type", create_type=False)),
            nullable=False,
        ),
        sa.Column("applies_to_area_ids", postgresql.ARRAY(sa.Uuid()), nullable=True),
        sa.Column("template_ref", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        _ts("archived_at", nullable=True),
        _ts("created_at"),
        sa.UniqueConstraint("project_id", "key", name="uq_custom_fields_project_key"),
        sa.CheckConstraint("key ~ '^[a-z][a-z0-9_]{1,39}$'", name="ck_custom_fields_key"),
    )

    op.add_column(
        "tickets",
        sa.Column("custom_fields", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_tickets_custom_fields",
        "tickets",
        ["custom_fields"],
        postgresql_using="gin",
        postgresql_ops={"custom_fields": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_custom_fields", table_name="tickets")
    op.drop_column("tickets", "custom_fields")
    op.drop_table("custom_field_definitions")
    postgresql.ENUM(name="custom_field_type").drop(op.get_bind())
    op.drop_table("jobs")
    postgresql.ENUM(name="job_status").drop(op.get_bind())
    _execute_script(DROP_PROCRASTINATE)
