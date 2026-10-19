"""append-only audit log; only a dedicated role may delete (retention)

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RETENTION_ROLE = "radicle_audit_retention"


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_project", "audit_log", ["project_id", "created_at"])
    op.create_index("ix_audit_log_action", "audit_log", ["action", "created_at"])
    # A role with no login that may delete expired rows; the app switches to it only in the
    # retention job. Roles are cluster-wide, so it may already exist.
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radicle_audit_retention') THEN
            CREATE ROLE radicle_audit_retention NOLOGIN;
          END IF;
          EXECUTE format('GRANT radicle_audit_retention TO %I', current_user);
        END $$
        """
    )
    op.execute(f"GRANT SELECT, DELETE ON audit_log TO {RETENTION_ROLE}")
    op.execute(
        f"""
        CREATE FUNCTION audit_log_append_only() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND current_user = '{RETENTION_ROLE}' THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'audit_log is append-only: % is not allowed', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_update_delete BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()"
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER audit_log_no_update_delete ON audit_log")
    op.execute("DROP FUNCTION audit_log_append_only()")
    op.execute(f"REVOKE ALL ON audit_log FROM {RETENTION_ROLE}")
    op.drop_table("audit_log")
    # The role stays: other databases of the cluster may use it.
