"""agents can be limited to a subset of MCP tools

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mcp_tools", postgresql.ARRAY(sa.Text()), nullable=True))
    op.create_check_constraint(
        "ck_users_mcp_tools_agents_only", "users", "mcp_tools IS NULL OR kind::text = 'agent'"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_mcp_tools_agents_only", "users", type_="check")
    op.drop_column("users", "mcp_tools")
