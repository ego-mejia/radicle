"""ticket start date, status periods (backfilled from history) and daily counts

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from radicle.services import period_builder

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("start_date", sa.Date(), nullable=True))
    op.create_table(
        "ticket_status_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Uuid(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status_id",
            sa.Uuid(),
            sa.ForeignKey("statuses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category", postgresql.ENUM(name="status_category", create_type=False), nullable=False
        ),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_status_periods_ticket", "ticket_status_periods", ["ticket_id", "entered_at"]
    )
    op.create_index(
        "ix_status_periods_status", "ticket_status_periods", ["status_id", "entered_at"]
    )
    op.create_table(
        "daily_status_counts",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status_id",
            sa.Uuid(),
            sa.ForeignKey("statuses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("milestone_key", sa.Uuid(), nullable=False),
        sa.Column("sprint_key", sa.Uuid(), nullable=False),
        sa.Column("ticket_count", sa.Integer(), nullable=False),
        sa.Column("remaining_hours", sa.Numeric(10, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "date", "project_id", "status_id", "milestone_key", "sprint_key", name="pk_daily_counts"
        ),
    )
    _backfill_periods()


def _backfill_periods() -> None:
    """Rebuild every ticket's periods from its history, with the same builder the
    application uses (`radicle backfill-periods` does the same later)."""
    conn = op.get_bind()
    statuses = conn.execute(
        sa.text(
            "SELECT s.id, s.ticket_type::text, s.name, s.category::text, p.key "
            "FROM statuses s JOIN projects p ON p.id = s.project_id"
        )
    ).all()
    by_name = {
        (str(key).upper(), ticket_type, str(name).lower()): (sid, category)
        for sid, ticket_type, name, category, key in statuses
    }

    def resolve(project_key, ticket_type, name):  # type: ignore[no-untyped-def]
        return by_name.get(((project_key or "").upper(), ticket_type, name.lower()), (None, "todo"))

    tickets = conn.execute(
        sa.text(
            "SELECT t.id, t.type::text, p.key FROM tickets t JOIN projects p ON p.id = t.project_id"
        )
    ).all()
    events: dict = {}
    rows = conn.execute(
        sa.text(
            "SELECT ticket_id, event_type, old_value, new_value, created_at "
            "FROM ticket_events ORDER BY ticket_id, id"
        )
    )
    for ticket_id, event_type, old, new, at in rows:
        events.setdefault(ticket_id, []).append(period_builder.Event(event_type, old, new, at))
    insert = sa.text(
        "INSERT INTO ticket_status_periods (id, ticket_id, status_id, category, entered_at, "
        "exited_at) VALUES (gen_random_uuid(), :ticket, :status, "
        "CAST(:category AS status_category), :entered, :exited)"
    )
    for ticket_id, ticket_type, key in tickets:
        for p in period_builder.build(
            events.get(ticket_id, []), ticket_type=ticket_type, project_key=key, resolve=resolve
        ):
            conn.execute(
                insert,
                {
                    "ticket": ticket_id,
                    "status": p.status_id,
                    "category": p.category,
                    "entered": p.entered_at,
                    "exited": p.exited_at,
                },
            )


def downgrade() -> None:
    op.drop_table("daily_status_counts")
    op.drop_index("ix_status_periods_status", table_name="ticket_status_periods")
    op.drop_index("ix_status_periods_ticket", table_name="ticket_status_periods")
    op.drop_table("ticket_status_periods")
    op.drop_column("tickets", "start_date")
