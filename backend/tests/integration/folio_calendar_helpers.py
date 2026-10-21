"""Shared setup for the calendar tests (Folio 5.8)."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.calendars import FolioCalendar
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import calendars
from radicle.folio.services.calendars import CalendarData
from radicle.platform.db.models import User
from tests.conftest import Team
from tests.integration.folio_helpers import API


def at(day: int, hour: int = 0, month: int = 12) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


async def user(db: AsyncSession, handle: str) -> User:
    found = await db.scalar(select(User).where(User.handle == handle))
    assert found is not None
    return found


async def eng_space(client: AsyncClient, db: AsyncSession, team: Team) -> FolioSpace:
    """Space eng: vera views; ana and luis are creators who may add events; olga sees nothing."""
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    grants = [{"grantee_type": "user", "grantee": team.viewer.handle, "permissions": ["view"]}]
    for handle in (team.admin.handle, team.member.handle):
        r = await client.post(
            f"{API}/admin/grants",
            headers=i,
            json={"grantee_type": "user", "grantee": handle, "role": "creator"},
        )
        assert r.status_code == 201, r.text
        grants.append(
            {"grantee_type": "user", "grantee": handle, "permissions": ["view", "create"]}
        )
    grants.append(
        {"grantee_type": "user", "grantee": team.instance.handle, "permissions": ["admin"]}
    )
    r = await client.put(f"{API}/spaces/eng/grants", headers=i, json={"grants": grants})
    assert r.status_code == 200, r.text
    found = await db.scalar(select(FolioSpace).where(FolioSpace.key == "eng"))
    assert found is not None
    return found


@pytest.fixture
async def releases(client: AsyncClient, db: AsyncSession, board: Team) -> FolioCalendar:
    """Calendar Releases in eng, showing project PA (milestone V1 is due 2026-12-15)."""
    space = await eng_space(client, db, board)
    admin = await user(db, board.instance.handle)
    data = CalendarData(name="Releases", color="green", docket_projects=["pa", "PA"])
    return await calendars.create_calendar(db, admin, space, data)
