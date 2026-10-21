"""People you can mention in Folio (Folio 2.3)."""

from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioGlobalGrant
from tests.conftest import Team

URL = "/api/v1/folio/people"


async def test_people_who_read_folio(client: AsyncClient, team: Team) -> None:
    r = await client.get(URL, params={"q": "lu"}, headers=team.member.headers)
    assert r.status_code == 200, r.text
    assert [p["handle"] for p in r.json()["items"]] == ["luis"]
    r = await client.get(URL, params={"q": "@agent"}, headers=team.member.headers)
    assert r.json()["items"][0] == {
        "handle": "agent-backend",
        "name": r.json()["items"][0]["name"],
        "kind": "agent",
    }
    everyone = (await client.get(URL, headers=team.member.headers)).json()["items"]
    assert 1 < len(everyone) <= 10


async def test_without_folio_nobody_is_listed(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await db.execute(delete(FolioGlobalGrant))
    r = await client.get(URL, headers=team.instance.headers)  # instance admins keep Folio
    assert [p["handle"] for p in r.json()["items"]] == [team.instance.handle]
    # Last: an error response rolls the shared test session back.
    r = await client.get(URL, headers=team.member.headers)
    assert r.status_code == 404
