"""Aggregate counts used by project and milestone views."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import Status, StatusCategory, Ticket


async def milestone_category_counts(
    db: AsyncSession, milestone_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, int]]:
    """Live tickets per status category for each milestone."""
    if not milestone_ids:
        return {}
    rows = await db.execute(
        select(Ticket.milestone_id, Status.category, func.count())
        .join(Status, Status.id == Ticket.status_id)
        .where(Ticket.milestone_id.in_(milestone_ids), Ticket.deleted_at.is_(None))
        .group_by(Ticket.milestone_id, Status.category)
    )
    result: dict[uuid.UUID, dict[str, int]] = {}
    for milestone_id, category, count in rows.all():
        if milestone_id is None:  # pragma: no cover - filtered by the IN clause
            continue
        result.setdefault(milestone_id, {})[StatusCategory(category).value] = int(count)
    return result


async def open_ticket_counts(
    db: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Live tickets not in a done status, per project."""
    if not project_ids:
        return {}
    rows = await db.execute(
        select(Ticket.project_id, func.count())
        .join(Status, Status.id == Ticket.status_id)
        .where(
            Ticket.project_id.in_(project_ids),
            Ticket.deleted_at.is_(None),
            Status.category != StatusCategory.done,
        )
        .group_by(Ticket.project_id)
    )
    return {project_id: int(count) for project_id, count in rows.all()}
