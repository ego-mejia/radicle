"""tickets, collaborators, mentions and append-only history

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from radicle.db.models.tickets import SEARCH_VECTOR_SQL

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=None if nullable else sa.func.now(),
    )


def upgrade() -> None:
    priority = postgresql.ENUM("highest", "high", "medium", "low", "lowest", name="priority")
    priority.create(op.get_bind())

    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("type", _enum("ticket_type", "task", "bug", "draft"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("status_id", sa.Uuid(), sa.ForeignKey("statuses.id"), nullable=False),
        sa.Column(
            "resolution",
            _enum("resolution", "done", "wont_do", "duplicate", "cannot_reproduce"),
            nullable=True,
        ),
        sa.Column("priority", _enum("priority"), nullable=False, server_default="medium"),
        sa.Column("area_id", sa.Uuid(), sa.ForeignKey("areas.id"), nullable=True, index=True),
        sa.Column(
            "milestone_id", sa.Uuid(), sa.ForeignKey("milestones.id"), nullable=True, index=True
        ),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=True, index=True),
        sa.Column("assignee_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("reporter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True, index=True),
        sa.Column("estimate_hours", sa.Numeric(7, 2), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("rank", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_SQL, persisted=True),
            nullable=True,
        ),
        _ts("created_at"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        _ts("resolved_at", nullable=True),
        _ts("deleted_at", nullable=True),
        sa.UniqueConstraint("project_id", "number", name="uq_tickets_project_number"),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 255", name="ck_tickets_title"),
        sa.CheckConstraint(
            "estimate_hours IS NULL OR estimate_hours BETWEEN 0 AND 9999",
            name="ck_tickets_estimate",
        ),
        sa.CheckConstraint("cardinality(tags) <= 20", name="ck_tickets_tags"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_tickets_parent"),
    )
    op.create_index("ix_tickets_tags", "tickets", ["tags"], postgresql_using="gin")
    op.create_index(
        "ix_tickets_search_vector", "tickets", ["search_vector"], postgresql_using="gin"
    )
    op.create_index(
        "ix_tickets_title_trgm",
        "tickets",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index("ix_tickets_project_status", "tickets", ["project_id", "status_id"])
    op.create_index("ix_tickets_project_rank", "tickets", ["project_id", "rank"])

    op.create_table(
        "ticket_collaborators",
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            index=True,
        ),
        _ts("created_at"),
    )

    op.create_table(
        "mentions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("comment_id", sa.Uuid(), nullable=True, index=True),
        sa.Column(
            "mentioned_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        _ts("created_at"),
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        _ts("created_at"),
    )
    op.create_index("ix_ticket_events_ticket_id_id", "ticket_events", ["ticket_id", "id"])
    op.execute(
        """
        CREATE FUNCTION ticket_events_append_only() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'ticket_events is append-only: % is not allowed', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER ticket_events_no_update_delete BEFORE UPDATE OR DELETE ON ticket_events "
        "FOR EACH ROW EXECUTE FUNCTION ticket_events_append_only()"
    )
    op.execute(
        "CREATE TRIGGER ticket_events_no_truncate BEFORE TRUNCATE ON ticket_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION ticket_events_append_only()"
    )


def downgrade() -> None:
    op.drop_table("ticket_events")
    op.execute("DROP FUNCTION ticket_events_append_only()")
    op.drop_table("mentions")
    op.drop_table("ticket_collaborators")
    op.drop_table("tickets")
    postgresql.ENUM(name="priority").drop(op.get_bind())
