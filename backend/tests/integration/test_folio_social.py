"""Following, favorites, reactions and reading history (Folio 2.4, 2.7)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def pages(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    made = {}
    for title in ("Guía", "Otra", "Secreta"):
        r = await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
        )
        made[title] = r.json()["id"]
        await publish(client, team, made[title])
    space = (await client.get(f"{API}/spaces/docs", headers=i)).json()
    return made | {"space": space}


async def _restrict(client: AsyncClient, team: Team, node: str) -> None:
    body = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    r = await client.put(
        f"{API}/nodes/{node}/restrictions", headers=team.instance.headers, json=body
    )
    assert r.status_code == 200, r.text


async def test_watch_and_auto_watch(client: AsyncClient, team: Team, pages: dict) -> None:
    i, m = team.instance.headers, team.member.headers
    url = f"{API}/watch/node/{pages['Guía']}"
    assert (await client.get(url, headers=i)).json() == {"watching": True}  # the author
    assert (await client.get(url, headers=m)).json() == {"watching": False}
    assert (await client.put(url, headers=m)).status_code == 204
    assert (await client.put(url, headers=m)).status_code == 204  # idempotent
    assert (await client.get(url, headers=m)).json() == {"watching": True}
    assert (await client.delete(url, headers=m)).status_code == 204
    assert (await client.get(url, headers=m)).json() == {"watching": False}


async def test_reactions(client: AsyncClient, team: Team, pages: dict) -> None:
    i, m = team.instance.headers, team.member.headers
    base = f"{API}/reactions/node/{pages['Guía']}"
    await client.put(f"{base}/👍", headers=i)
    got = (await client.put(f"{base}/👍", headers=m)).json()
    assert got == [{"emoji": "👍", "count": 2, "mine": True}]
    got = (await client.put(f"{base}/🎉", headers=m)).json()
    assert [r["emoji"] for r in got] == ["👍", "🎉"]
    got = (await client.delete(f"{base}/👍", headers=m)).json()
    assert got[0] == {"emoji": "👍", "count": 1, "mine": False}
    r = await client.put(f"{base}/💩", headers=m)
    assert r.status_code == 422 and "👍" in r.json()["detail"]


async def test_favorites_and_recents(
    client: AsyncClient, db: AsyncSession, team: Team, pages: dict
) -> None:
    m = team.member.headers
    await client.put(f"{API}/favorites/node/{pages['Guía']}", headers=m)
    await client.put(f"{API}/favorites/space/{pages['space']['key']}", headers=m)
    space_id = (await client.get(f"{API}/nodes/{pages['Guía']}", headers=m)).json()["space"]
    assert space_id == "docs"
    for title in ("Otra", "Guía", "Otra", "Secreta"):
        await client.get(f"{API}/nodes/{pages[title]}", headers=m)
    recents = (await client.get(f"{API}/me/recents", headers=m)).json()["items"]
    assert [n["title"] for n in recents] == ["Secreta", "Otra", "Guía"]  # once each
    await _restrict(client, team, pages["Secreta"])
    recents = (await client.get(f"{API}/me/recents", headers=m)).json()["items"]
    assert "Secreta" not in [n["title"] for n in recents]
    favs = (await client.get(f"{API}/me/favorites", headers=m)).json()
    assert [n["title"] for n in favs["nodes"]] == ["Guía"]
    await client.delete(f"{API}/favorites/node/{pages['Guía']}", headers=m)
    favs = (await client.get(f"{API}/me/favorites", headers=m)).json()
    assert favs["nodes"] == []


async def test_errors(client: AsyncClient, team: Team, pages: dict) -> None:
    m = team.member.headers
    await _restrict(client, team, pages["Secreta"])
    for url in (
        f"{API}/watch/node/{pages['Secreta']}",
        f"{API}/favorites/node/{pages['Secreta']}",
        f"{API}/reactions/node/{pages['Secreta']}/👍",
    ):
        assert (await client.put(url, headers=m)).status_code == 404, url
    r = await client.put(f"{API}/watch/comment/{pages['Guía']}", headers=m)
    assert r.status_code == 422
