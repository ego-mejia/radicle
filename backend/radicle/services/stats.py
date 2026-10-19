"""Aggregate counts used by project and milestone views."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def milestone_category_counts(
    db: AsyncSession, milestone_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, int]]:
    """Tickets per status category for each milestone. Filled in once tickets exist (1.3)."""
    del db, milestone_ids
    return {}


async def open_ticket_counts(
    db: AsyncSession, project_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Tickets not in a done status, per project. Filled in once tickets exist (1.3)."""
    del db, project_ids
    return {}
