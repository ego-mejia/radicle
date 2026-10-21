"""Folio analytics (phase 5.9): page views per day, what people search for and don't find,
and the site's most read content. Owners and space admins see a page's numbers; readers'
names only where the space allows it. The site dashboard is for Folio admins."""

import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.analytics import FolioPageView, FolioSearchLog
from radicle.folio.db.models import FolioNode
from radicle.folio.services import access, publishing, quality
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed

WORDS_PER_MINUTE = 200
MAX_DAYS = 365
QUERY_MAX = 500


def _days(days: int) -> int:
    if not 1 <= days <= MAX_DAYS:
        raise ValidationFailed(
            f"Analytics cover 1 to {MAX_DAYS} days; {days} is out of range.",
            errors=[{"field": "days", "message": "out of range"}],
        )
    return days


async def record_view(db: AsyncSession, user: User, node: FolioNode) -> None:
    """One more view of the page today by this reader (the caller checked they can see it)."""
    await db.execute(
        insert(FolioPageView)
        .values(node_id=node.id, user_id=user.id, day=quality.today(), views=1)
        .on_conflict_do_update(
            index_elements=["node_id", "user_id", "day"],
            set_={"views": FolioPageView.views + 1},
        )
    )


async def log_search(
    db: AsyncSession, user: User, query: str, mode: str, results_count: int
) -> FolioSearchLog:
    entry = FolioSearchLog(
        user_id=user.id, query=query.strip()[:QUERY_MAX], mode=mode, results_count=results_count
    )
    db.add(entry)
    await db.flush()
    return entry


async def record_click(
    db: AsyncSession, user: User, search_id: uuid.UUID, node_id: uuid.UUID
) -> None:
    """The result the user opened from one of their searches."""
    entry = await db.get(FolioSearchLog, search_id)
    if entry is None or entry.user_id != user.id:
        raise NotFound(f"Search {search_id} not found.", code="search_not_found")
    if not await access.can_view(db, user, node_id):
        raise NotFound(f"Page {node_id} not found.", code="node_not_found")
    entry.clicked_node_id = node_id
    await db.flush()


@dataclass(frozen=True)
class Day:
    day: date
    views: int
    unique: int


@dataclass(frozen=True)
class Reader:
    handle: str
    name: str
    views: int
    last_day: date


@dataclass(frozen=True)
class PageStats:
    days: int
    views: int
    unique_readers: int
    daily: list[Day]
    reading_minutes: int
    readers_visible: bool
    readers: list[Reader]


def _since(days: int) -> date:
    return quality.today() - timedelta(days=days - 1)


def _daily(rows: list[Any], days: int) -> list[Day]:
    """Every day of the range, zeros included, so a chart has no gaps."""
    by_day = {r.day: Day(r.day, int(r.views), int(r.unique)) for r in rows}
    start = _since(days)
    return [
        by_day.get(start + timedelta(days=n), Day(start + timedelta(days=n), 0, 0))
        for n in range(days)
    ]


async def _reading_minutes(db: AsyncSession, node: FolioNode) -> int:
    version = await publishing.current_version(db, node)
    words = len(version.content_text.split()) if version else 0
    return max(1, math.ceil(words / WORDS_PER_MINUTE)) if words else 0


async def page_stats(db: AsyncSession, user: User, node: FolioNode, days: int = 30) -> PageStats:
    space = await quality.require_owner_or_admin(db, user, node)
    days = _days(days)
    since = _since(days)
    in_range = (FolioPageView.node_id == node.id, FolioPageView.day >= since)
    daily = await db.execute(
        select(
            FolioPageView.day,
            func.sum(FolioPageView.views).label("views"),
            func.count().label("unique"),
        )
        .where(*in_range)
        .group_by(FolioPageView.day)
    )
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(FolioPageView.views), 0),
                func.count(distinct(FolioPageView.user_id)),
            ).where(*in_range)
        )
    ).one()
    readers: list[Reader] = []
    if space.show_readers:
        rows = await db.execute(
            select(
                User.handle,
                User.display_name,
                func.sum(FolioPageView.views),
                func.max(FolioPageView.day),
            )
            .join(User, User.id == FolioPageView.user_id)
            .where(*in_range)
            .group_by(User.id)
            .order_by(func.max(FolioPageView.day).desc(), User.handle)
            .limit(100)
        )
        readers = [Reader(h, n, int(v), d) for h, n, v, d in rows.all()]
    return PageStats(
        days=days,
        views=int(totals[0]),
        unique_readers=int(totals[1]),
        daily=_daily(list(daily.all()), days),
        reading_minutes=await _reading_minutes(db, node),
        readers_visible=space.show_readers,
        readers=readers,
    )
