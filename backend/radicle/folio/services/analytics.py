"""Folio analytics (phase 5.9): page views per day, what people search for and don't find,
and the site's most read content. Owners and space admins see a page's numbers; readers'
names only where the space allows it. The site dashboard is for Folio admins."""

import math
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, distinct, func, select, union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.analytics import FolioPageView, FolioSearchLog
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import access, chat, publishing, quality
from radicle.platform import authz
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


@dataclass(frozen=True)
class SpaceActivity:
    key: str
    name: str
    views: int
    readers: int


@dataclass(frozen=True)
class TopPage:
    node_id: uuid.UUID
    title: str
    space: str
    views: int
    readers: int


@dataclass(frozen=True)
class SearchGap:
    query: str
    times: int
    last_at: datetime


@dataclass(frozen=True)
class SiteStats:
    days: int
    views: int
    active_users: int
    daily: list[Day]
    top_spaces: list[SpaceActivity]
    top_pages: list[TopPage]
    searches: int
    no_results: list[SearchGap]
    unanswered: list[chat.Unanswered]


async def _require_admin(db: AsyncSession, user: User) -> None:
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()


def _gaps_query(since: date, limit: int) -> Select[Any]:
    normalized = func.lower(func.btrim(FolioSearchLog.query))
    return (
        select(normalized, func.count(), func.max(FolioSearchLog.created_at))
        .where(FolioSearchLog.results_count == 0, FolioSearchLog.created_at >= since)
        .group_by(normalized)
        .order_by(func.count().desc(), func.max(FolioSearchLog.created_at).desc())
        .limit(limit)
    )


async def search_gaps(
    db: AsyncSession, user: User, days: int = 30, limit: int = 20
) -> tuple[list[SearchGap], list[chat.Unanswered]]:
    """What people searched without a result, most often first, and the chat questions the
    docs didn't answer: the list of what to document next."""
    await _require_admin(db, user)
    since = _since(_days(days))
    rows = await db.execute(_gaps_query(since, limit))
    gaps = [SearchGap(q, int(n), at) for q, n, at in rows.all()]
    return gaps, await chat.unanswered(db, user, limit=limit)


async def site_stats(db: AsyncSession, user: User, days: int = 30) -> SiteStats:
    await _require_admin(db, user)
    days = _days(days)
    since = _since(days)
    in_range = FolioPageView.day >= since
    visible = await access.node_filter(db, user)
    daily = await db.execute(
        select(
            FolioPageView.day,
            func.sum(FolioPageView.views).label("views"),
            func.count(distinct(FolioPageView.user_id)).label("unique"),
        )
        .where(in_range)
        .group_by(FolioPageView.day)
    )
    views = await db.scalar(select(func.coalesce(func.sum(FolioPageView.views), 0)).where(in_range))
    people = union(
        select(FolioPageView.user_id).where(in_range),
        select(FolioSearchLog.user_id).where(
            FolioSearchLog.created_at >= since, FolioSearchLog.user_id.is_not(None)
        ),
    ).subquery()
    active = await db.scalar(select(func.count()).select_from(people))
    spaces = await db.execute(
        select(
            FolioSpace.key,
            FolioSpace.name,
            func.sum(FolioPageView.views),
            func.count(distinct(FolioPageView.user_id)),
        )
        .join(FolioNode, FolioNode.id == FolioPageView.node_id)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .where(in_range, visible)
        .group_by(FolioSpace.id)
        .order_by(func.sum(FolioPageView.views).desc(), FolioSpace.key)
        .limit(10)
    )
    pages = await db.execute(
        select(
            FolioNode.id,
            FolioNode.title,
            FolioSpace.key,
            func.sum(FolioPageView.views),
            func.count(distinct(FolioPageView.user_id)),
        )
        .join(FolioNode, FolioNode.id == FolioPageView.node_id)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .where(in_range, visible)
        .group_by(FolioNode.id, FolioSpace.key)
        .order_by(func.sum(FolioPageView.views).desc(), FolioNode.title)
        .limit(10)
    )
    searches = await db.scalar(
        select(func.count()).select_from(FolioSearchLog).where(FolioSearchLog.created_at >= since)
    )
    gaps, unanswered = await search_gaps(db, user, days)
    return SiteStats(
        days=days,
        views=int(views or 0),
        active_users=int(active or 0),
        daily=_daily(list(daily.all()), days),
        top_spaces=[SpaceActivity(k, n, int(v), int(r)) for k, n, v, r in spaces.all()],
        top_pages=[TopPage(i, t, k, int(v), int(r)) for i, t, k, v, r in pages.all()],
        searches=int(searches or 0),
        no_results=gaps,
        unanswered=unanswered,
    )
