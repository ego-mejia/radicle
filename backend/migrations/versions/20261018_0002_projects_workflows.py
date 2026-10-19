"""projects, members, areas, milestones, statuses and transitions

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS = {
    "project_role": ("admin", "member", "viewer"),
    "ticket_type": ("task", "bug", "draft"),
    "status_category": ("todo", "in_progress", "done"),
    "resolution": ("done", "wont_do", "duplicate", "cannot_reproduce"),
    "milestone_status": ("open", "closed"),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def _project_fk() -> sa.Column:
    return sa.Column(
        "project_id",
        sa.Uuid(),
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("ticket_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("archived_at", nullable=True),
        sa.CheckConstraint("key::text ~ '^[A-Z][A-Z0-9]{1,9}$'", name="ck_projects_key"),
    )
    # The key is part of every ticket key, so it can never change.
    op.execute(
        """
        CREATE FUNCTION projects_key_immutable() RETURNS trigger AS $$
        BEGIN
          IF NEW.key IS DISTINCT FROM OLD.key THEN
            RAISE EXCEPTION 'project key is immutable';
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER projects_key_immutable BEFORE UPDATE ON projects "
        "FOR EACH ROW EXECUTE FUNCTION projects_key_immutable()"
    )

    op.create_table(
        "project_members",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
        sa.Column("role", _enum("project_role"), nullable=False),
        _ts("created_at"),
    )

    op.create_table(
        "areas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _project_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        _ts("archived_at", nullable=True),
        _ts("created_at"),
        sa.CheckConstraint("color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_areas_color"),
    )
    op.create_index(
        "uq_areas_project_name", "areas", ["project_id", sa.text("lower(name)")], unique=True
    )

    op.create_table(
        "milestones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _project_fk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", _enum("milestone_status"), nullable=False, server_default="open"),
        _ts("closed_at", nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        _ts("created_at"),
    )
    op.create_index(
        "uq_milestones_project_name",
        "milestones",
        ["project_id", sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "statuses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _project_fk(),
        sa.Column("ticket_type", _enum("ticket_type"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", _enum("status_category"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_initial", sa.Boolean(), nullable=False, server_default="false"),
        _ts("created_at"),
    )
    op.create_index(
        "uq_statuses_project_type_name",
        "statuses",
        ["project_id", "ticket_type", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "uq_statuses_initial",
        "statuses",
        ["project_id", "ticket_type"],
        unique=True,
        postgresql_where=sa.text("is_initial"),
    )

    op.create_table(
        "transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _project_fk(),
        sa.Column("ticket_type", _enum("ticket_type"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "from_status_id",
            sa.Uuid(),
            sa.ForeignKey("statuses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "to_status_id",
            sa.Uuid(),
            sa.ForeignKey("statuses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("allowed_resolutions", postgresql.ARRAY(_enum("resolution")), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        _ts("created_at"),
    )


def downgrade() -> None:
    op.drop_table("transitions")
    op.drop_table("statuses")
    op.drop_table("milestones")
    op.drop_table("areas")
    op.drop_table("project_members")
    op.execute("DROP TRIGGER projects_key_immutable ON projects")
    op.execute("DROP FUNCTION projects_key_immutable()")
    op.drop_table("projects")
    bind = op.get_bind()
    for name in reversed(ENUMS):
        postgresql.ENUM(name=name).drop(bind)
