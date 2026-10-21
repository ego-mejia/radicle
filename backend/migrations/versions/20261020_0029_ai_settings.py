"""The instance's AI provider for chat and embeddings

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-20

Folio 0.3. One row; the API key is stored encrypted.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ai_provider = postgresql.ENUM(
    "none",
    "anthropic",
    "openai",
    "openai_compatible",
    "ollama",
    name="ai_provider",
    create_type=False,
)


def upgrade() -> None:
    ai_provider.create(op.get_bind())
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", ai_provider, nullable=False, server_default="none"),
        sa.Column("chat_model", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "features", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("id = 1", name="ck_ai_settings_single_row"),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
    ai_provider.drop(op.get_bind())
