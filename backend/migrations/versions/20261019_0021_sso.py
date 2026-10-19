"""SSO providers, user SSO identity and instance settings

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sso_providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("issuer_url", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("allowed_domains", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("auto_create_users", sa.Boolean(), nullable=False),
        sa.Column("group_claim", sa.Text(), nullable=True),
        sa.Column("group_mapping", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "instance_settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "users", sa.Column("auth_source", sa.Text(), nullable=False, server_default="local")
    )
    op.add_column(
        "users",
        sa.Column(
            "sso_provider_id",
            sa.Uuid(),
            sa.ForeignKey("sso_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("sso_subject", sa.Text(), nullable=True))
    op.create_index(
        "uq_users_sso_subject", "users", ["sso_provider_id", "sso_subject"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_users_sso_subject", table_name="users")
    op.drop_column("users", "sso_subject")
    op.drop_column("users", "sso_provider_id")
    op.drop_column("users", "auth_source")
    op.drop_table("instance_settings")
    op.drop_table("sso_providers")
