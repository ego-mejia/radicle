"""Folio chat: sessions and messages with citations, retrieval and feedback

Revision ID: 0051
Revises: 0050
Create Date: 2026-10-21

Folio phase 4 (4.5).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = postgresql.ENUM("user", "assistant", name="folio_chat_role", create_type=False)
FEEDBACK = postgresql.ENUM("up", "down", name="folio_chat_feedback", create_type=False)


def upgrade() -> None:
    ROLE.create(op.get_bind())
    FEEDBACK.create(op.get_bind())
    op.create_table(
        "folio_chat_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_folio_chat_sessions_user", "folio_chat_sessions", ["user_id", "updated_at"])
    op.create_table(
        "folio_chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("folio_chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", ROLE, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("retrieval", postgresql.JSONB(), nullable=False),
        sa.Column("feedback", FEEDBACK, nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_folio_chat_messages_session", "folio_chat_messages", ["session_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("folio_chat_messages")
    op.drop_table("folio_chat_sessions")
    FEEDBACK.drop(op.get_bind())
    ROLE.drop(op.get_bind())
