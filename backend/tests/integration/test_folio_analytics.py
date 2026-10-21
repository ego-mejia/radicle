"""Folio analytics (5.9): page views per day, readers only where the space allows it, and
the result a search led to."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import analytics
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Clock, Team
from tests.integration.folio_helpers import API, publish


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def page(client: AsyncClient, db: AsyncSession, team: Team) -> FolioNode:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    await publish(client, team, r.json()["id"], md="# Deploy\n\n" + "palabra " * 450)
    node = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert node is not None
    return node


async def test_views_per_day_and_readers_only_when_the_space_allows(
    db: AsyncSession, team: Team, page: FolioNode, clock: Clock
) -> None:
    member = await _user(db, team.member.handle)
    viewer = await _user(db, team.viewer.handle)
    admin = await _user(db, team.instance.handle)
    await analytics.record_view(db, member, page)
    clock.advance(days=-1)
    await analytics.record_view(db, member, page)
    await analytics.record_view(db, viewer, page)
    clock.advance(days=1)
    await analytics.record_view(db, member, page)

    stats = await analytics.page_stats(db, admin, page, days=7)
    assert (stats.views, stats.unique_readers) == (4, 2)
    assert len(stats.daily) == 7 and stats.daily[0].views == 0
    assert [(d.views, d.unique) for d in stats.daily[-2:]] == [(2, 2), (2, 1)]
    assert stats.reading_minutes == 3  # 451 words at 200 a minute
    assert not stats.readers_visible and stats.readers == []

    space = await db.get(FolioSpace, page.space_id)
    assert space is not None
    space.show_readers = True
    stats = await analytics.page_stats(db, admin, page, days=7)
    assert [(r.handle, r.views) for r in stats.readers] == [
        (team.member.handle, 3),
        (team.viewer.handle, 1),
    ]


async def test_only_the_owner_or_a_space_admin_sees_a_page_s_numbers(
    db: AsyncSession, team: Team, page: FolioNode
) -> None:
    member = await _user(db, team.member.handle)
    with pytest.raises(Forbidden):
        await analytics.page_stats(db, member, page)
    with pytest.raises(ValidationFailed):
        await analytics.page_stats(db, await _user(db, team.instance.handle), page, days=0)


async def test_a_click_belongs_to_your_own_search(
    db: AsyncSession, team: Team, page: FolioNode
) -> None:
    member = await _user(db, team.member.handle)
    viewer = await _user(db, team.viewer.handle)
    entry = await analytics.log_search(db, member, "deploy", "hybrid", 1)
    with pytest.raises(NotFound):
        await analytics.record_click(db, viewer, entry.id, page.id)
    with pytest.raises(NotFound):
        await analytics.record_click(db, member, entry.id, uuid.uuid4())
