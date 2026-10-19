"""groups, group roles in projects and the per-project permission matrix

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = postgresql.ENUM(name="project_role", create_type=False)


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "group_members",
        sa.Column(
            "group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
    )
    op.create_table(
        "project_group_roles",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_id",
            sa.Uuid(),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
        sa.Column("role", ROLE, nullable=False),
    )
    op.create_table(
        "project_role_permissions",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", ROLE, primary_key=True),
        sa.Column("permission", sa.Text(), primary_key=True),
        sa.Column("allowed", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_project_role_permissions_project", "project_role_permissions", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_project_role_permissions_project", table_name="project_role_permissions")
    op.drop_table("project_role_permissions")
    op.drop_table("project_group_roles")
    op.drop_table("group_members")
    op.drop_table("groups")
