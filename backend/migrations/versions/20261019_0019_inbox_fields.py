"""inbox fields on tickets: origin, classification, impact, effort, conversion

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORIGIN = postgresql.ENUM("team", "user", name="ticket_origin")
CLASSIFICATION = postgresql.ENUM(
    "idea", "experiment", "complaint", "suggestion", name="classification"
)


def upgrade() -> None:
    ORIGIN.create(op.get_bind())
    CLASSIFICATION.create(op.get_bind())
    origin = postgresql.ENUM(name="ticket_origin", create_type=False)
    classification = postgresql.ENUM(name="classification", create_type=False)
    op.add_column("tickets", sa.Column("origin", origin, nullable=True))
    op.add_column("tickets", sa.Column("classification", classification, nullable=True))
    op.add_column("tickets", sa.Column("impact", sa.SmallInteger(), nullable=True))
    op.add_column("tickets", sa.Column("effort", sa.SmallInteger(), nullable=True))
    op.add_column("tickets", sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("submitter_name", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("submitter_email", postgresql.CITEXT(), nullable=True))
    op.add_column("tickets", sa.Column("tracking_code", sa.Text(), nullable=True))
    op.add_column("tickets", sa.Column("public_comment", sa.Text(), nullable=True))
    op.create_unique_constraint("tickets_tracking_code_key", "tickets", ["tracking_code"])
    op.create_check_constraint(
        "ck_tickets_impact_effort", "tickets", "impact BETWEEN 1 AND 5 AND effort BETWEEN 1 AND 5"
    )
    # Existing drafts came from the team; call them ideas.
    op.execute("UPDATE tickets SET origin = 'team', classification = 'idea' WHERE type = 'draft'")


def downgrade() -> None:
    op.drop_constraint("ck_tickets_impact_effort", "tickets", type_="check")
    op.drop_constraint("tickets_tracking_code_key", "tickets", type_="unique")
    for column in (
        "public_comment",
        "tracking_code",
        "submitter_email",
        "submitter_name",
        "converted_at",
        "effort",
        "impact",
        "classification",
        "origin",
    ):
        op.drop_column("tickets", column)
    CLASSIFICATION.drop(op.get_bind())
    ORIGIN.drop(op.get_bind())
