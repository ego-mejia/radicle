"""Read counts (Folio 2.7): folio_views rolled up per page and day for "Most read".

The job recomputes yesterday and today from the raw views every hour, so running it
twice, or late, gives the same numbers.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioView, FolioViewCountDaily
from radicle.platform.db.models import utcnow
from radicle.platform.services import queue

COUNT_JOB = "folio_view_counts"


async def count_day(db: AsyncSession, day: date) -> int:
    """Write the day's views and unique viewers per page; returns how many pages."""
    start = datetime.combine(day, time(), tzinfo=UTC)
    rows = (
        await db.execute(
            select(
                FolioView.node_id,
                func.count(),
                func.count(func.distinct(FolioView.user_id)),
            )
            .where(FolioView.viewed_at >= start, FolioView.viewed_at < start + timedelta(days=1))
            .group_by(FolioView.node_id)
        )
    ).all()
    for node_id, views, unique in rows:
        await db.execute(
            insert(FolioViewCountDaily)
            .values(node_id=node_id, date=day, views=views, unique_viewers=unique)
            .on_conflict_do_update(
                index_elements=["node_id", "date"],
                set_={"views": views, "unique_viewers": unique},
            )
        )
    return len(rows)


@queue.handler(COUNT_JOB)
async def count_recent(db: AsyncSession, **_: Any) -> None:
    today = utcnow().astimezone(UTC).date()
    for day in (today - timedelta(days=1), today):
        await count_day(db, day)


def most_read_since(days: int = 7) -> Any:
    """Views per page over the last `days` days, as a subquery (node_id, views)."""
    since = utcnow().astimezone(UTC).date() - timedelta(days=days - 1)
    return (
        select(FolioViewCountDaily.node_id, func.sum(FolioViewCountDaily.views).label("views"))
        .where(FolioViewCountDaily.date >= since)
        .group_by(FolioViewCountDaily.node_id)
        .subquery()
    )
