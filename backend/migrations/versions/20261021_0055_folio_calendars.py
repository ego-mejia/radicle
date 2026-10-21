"""Folio calendars and events

Revision ID: 0055
Revises: 0054
Create Date: 2026-10-21

Folio phase 5 (5.8). Calendars per space with events, Docket milestones and an iCal feed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

category = postgresql.ENUM(
    "vacation",
    "release",
    "event",
    "oncall",
    "other",
    name="folio_event_category",
    create_type=False,
)


def upgrade() -> None:
    category.create(op.get_bind())
    op.create_table(
        "folio_calendars",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "space_id",
            sa.Uuid(),
            sa.ForeignKey("folio_spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), server_default="blue", nullable=False),
        sa.Column(
            "docket_projects", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("ical_token", sa.Text(), nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_folio_calendars_space_id", "folio_calendars", ["space_id"])
    op.create_index("ux_folio_calendars_ical_token", "folio_calendars", ["ical_token"], unique=True)
    op.create_table(
        "folio_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "calendar_id",
            sa.Uuid(),
            sa.ForeignKey("folio_calendars.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("people", postgresql.ARRAY(sa.Uuid()), server_default="{}", nullable=False),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_folio_events_calendar_start", "folio_events", ["calendar_id", "start_at"])


def downgrade() -> None:
    op.drop_index("ix_folio_events_calendar_start", table_name="folio_events")
    op.drop_table("folio_events")
    op.drop_index("ux_folio_calendars_ical_token", table_name="folio_calendars")
    op.drop_index("ix_folio_calendars_space_id", table_name="folio_calendars")
    op.drop_table("folio_calendars")
    category.drop(op.get_bind())
