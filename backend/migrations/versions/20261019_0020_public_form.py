"""public inbox form: settings per project, submissions, ALTCHA replay guard, inbox user

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INBOX_USER_ID = "00000000-0000-0000-0000-000000000003"


def upgrade() -> None:
    postgresql.ENUM("altcha", "turnstile", "hcaptcha", "none", name="captcha").create(op.get_bind())
    op.create_table(
        "inbox_settings",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("public_slug", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("intro_md", sa.Text(), nullable=False),
        sa.Column("thank_you_md", sa.Text(), nullable=False),
        sa.Column("allowed_classifications", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("require_email", sa.Boolean(), nullable=False),
        sa.Column("allow_attachments", sa.Boolean(), nullable=False),
        sa.Column("max_attachments", sa.Integer(), nullable=False),
        sa.Column("captcha", postgresql.ENUM(name="captcha", create_type=False), nullable=False),
        sa.Column("captcha_config", postgresql.JSONB(), nullable=False),
        sa.Column("auto_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "inbox_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_inbox_submissions_ip", "inbox_submissions", ["ip_hash", "created_at"])
    op.create_table(
        "used_challenges",
        sa.Column("challenge", sa.Text(), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_used_challenges_expires_at", "used_challenges", ["expires_at"])
    # Reporter of public submissions: a system user that never signs in.
    op.execute(
        sa.text(
            "INSERT INTO users (id, handle, display_name, kind, is_active) "
            "VALUES (CAST(:id AS uuid), 'inbox', 'Inbox', 'system', false) "
            "ON CONFLICT DO NOTHING"
        ).bindparams(id=INBOX_USER_ID)
    )


def downgrade() -> None:
    # Tickets may name the inbox user as reporter; it stays, inactive.
    op.drop_index("ix_used_challenges_expires_at", table_name="used_challenges")
    op.drop_table("used_challenges")
    op.drop_index("ix_inbox_submissions_ip", table_name="inbox_submissions")
    op.drop_table("inbox_submissions")
    op.drop_table("inbox_settings")
    postgresql.ENUM(name="captcha").drop(op.get_bind())
