"""Folio analytics over REST (5.9): count a page view, record which search result was
opened, a page's numbers for its owner and space admins, and the site's for Folio admins."""

import uuid
from datetime import date

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.services import analytics, nodes
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime

router = APIRouter(tags=["folio"])

Days = Query(default=30, ge=1, le=analytics.MAX_DAYS, description="How many days back")


class ViewIn(Input):
    node_id: uuid.UUID


class SearchClickIn(Input):
    node_id: uuid.UUID = Field(description="The result that was opened")


class DayOut(Output):
    day: date
    views: int
    unique: int = Field(description="Distinct readers that day")


class ReaderOut(Output):
    handle: str
    name: str
    views: int
    last_day: date


class PageAnalyticsOut(Output):
    days: int
    views: int
    unique_readers: int
    daily: list[DayOut] = Field(description="Every day of the range, oldest first")
    reading_minutes: int = Field(description="Approximate, at 200 words a minute")
    readers_visible: bool = Field(description="False when the space only counts its readers")
    readers: list[ReaderOut]


class SpaceActivityOut(Output):
    key: str
    name: str
    views: int
    readers: int


class TopPageOut(Output):
    node_id: uuid.UUID
    title: str
    space: str
    views: int
    readers: int


class SearchGapOut(Output):
    query: str
    times: int
    last_at: UtcDatetime


class UnansweredQuestionOut(Output):
    question: str
    feedback: str | None
    asked_at: UtcDatetime


class SiteAnalyticsOut(Output):
    days: int
    views: int
    active_users: int = Field(description="People who read or searched in the range")
    daily: list[DayOut]
    top_spaces: list[SpaceActivityOut]
    top_pages: list[TopPageOut]
    searches: int
    no_results: list[SearchGapOut] = Field(description="Searched without a result")
    unanswered: list[UnansweredQuestionOut] = Field(
        description="Chat questions the docs didn't answer"
    )


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


def _days(rows: list[analytics.Day]) -> list[DayOut]:
    return [DayOut(day=d.day, views=d.views, unique=d.unique) for d in rows]


@router.post("/analytics/views", status_code=204)
async def record_view(body: ViewIn, principal: CurrentPrincipal, db: Db) -> Response:
    """The web app calls this when someone opens a page to read it."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, body.node_id)
    await analytics.record_view(db, principal.user, node)
    return Response(status_code=204)


@router.post("/analytics/searches/{search_id}/click", status_code=204)
async def record_click(
    search_id: uuid.UUID, body: SearchClickIn, principal: CurrentPrincipal, db: Db
) -> Response:
    """The result someone opened from a search (its `search_id`)."""
    await _reader(db, principal)
    await analytics.record_click(db, principal.user, search_id, body.node_id)
    return Response(status_code=204)


@router.get("/analytics/pages/{node_id}", response_model=PageAnalyticsOut)
async def page_analytics(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db, days: int = Days
) -> PageAnalyticsOut:
    """Views per day, unique readers and reading time; names of readers only where the
    space allows it. For the page owner and space admins."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    s = await analytics.page_stats(db, principal.user, node, days)
    return PageAnalyticsOut(
        days=s.days,
        views=s.views,
        unique_readers=s.unique_readers,
        daily=_days(s.daily),
        reading_minutes=s.reading_minutes,
        readers_visible=s.readers_visible,
        readers=[
            ReaderOut(handle=r.handle, name=r.name, views=r.views, last_day=r.last_day)
            for r in s.readers
        ],
    )


@router.get("/analytics/site", response_model=SiteAnalyticsOut)
async def site_analytics(principal: CurrentPrincipal, db: Db, days: int = Days) -> SiteAnalyticsOut:
    """Folio admins: activity, the most read content, and what people don't find."""
    await _reader(db, principal)
    s = await analytics.site_stats(db, principal.user, days)
    return SiteAnalyticsOut(
        days=s.days,
        views=s.views,
        active_users=s.active_users,
        daily=_days(s.daily),
        top_spaces=[
            SpaceActivityOut(key=a.key, name=a.name, views=a.views, readers=a.readers)
            for a in s.top_spaces
        ],
        top_pages=[
            TopPageOut(
                node_id=p.node_id, title=p.title, space=p.space, views=p.views, readers=p.readers
            )
            for p in s.top_pages
        ],
        searches=s.searches,
        no_results=[
            SearchGapOut(query=g.query, times=g.times, last_at=g.last_at) for g in s.no_results
        ],
        unanswered=[
            UnansweredQuestionOut(question=u.question, feedback=u.feedback, asked_at=u.asked_at)
            for u in s.unanswered
        ],
    )
