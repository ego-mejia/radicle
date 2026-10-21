"""Folio's home (Folio 1.8): the default bento, resolved per reader."""

from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioGlobalGrant
from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA


async def _doc(
    client: AsyncClient, team: Team, space: str, title: str, kind: str = "blog_post", **meta: object
) -> str:
    i = team.instance.headers
    body = {"space": space, "kind": kind, "title": title}
    nid = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
    words = " ".join(["palabra"] * 450)
    r = await client.put(
        f"{API}/nodes/{nid}/draft",
        headers=i,
        json={"content_md": f"# {title}\n\n{words}", "metadata": METADATA | meta},
    )
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})).status_code == 201
    return nid


async def _spaces(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    for key, name in (("eng", "Ingeniería"), ("ai-tools", "AI Tools")):
        await client.post(f"{API}/spaces", headers=i, json={"key": key, "name": name})


async def test_the_bento_resolves_every_block(client: AsyncClient, team: Team) -> None:
    await _spaces(client, team)
    welcome = await _doc(client, team, "eng", "Bienvenido", kind="page", labels=["featured"])
    news = await _doc(client, team, "eng", "V1 sale en noviembre", labels=["anuncio"])
    mcp = await _doc(client, team, "ai-tools", "Conecta Claude por MCP", kind="page")
    post = await _doc(client, team, "eng", "Cambios de la semana")

    r = await client.get(f"{API}/home", headers=team.member.headers)
    assert r.status_code == 200, r.text
    home = r.json()
    assert home["can_write"] is False
    assert home["featured"]["id"] == welcome and home["featured"]["reading_minutes"] == 2
    assert home["featured"]["author"] == "fernando" and home["featured"]["space_name"]
    assert home["announcement"]["id"] == news
    assert [c["id"] for c in home["ai_tools"]] == [mcp]
    assert [c["id"] for c in home["latest_posts"]] == [post, news]
    assert [c["id"] for c in home["most_read"]] == [post, mcp, news, welcome]
    assert {s["key"]: s["docs"] for s in home["spaces"]} == {"ai-tools": 1, "eng": 3}
    admin = (await client.get(f"{API}/home", headers=team.instance.headers)).json()
    assert admin["can_write"] is True


async def test_an_empty_folio(client: AsyncClient, team: Team) -> None:
    home = (await client.get(f"{API}/home", headers=team.member.headers)).json()
    assert home["featured"] is None and home["announcement"] is None
    assert home["latest_posts"] == [] and home["spaces"] == []


async def test_without_an_announcement_the_latest_post_is_featured(
    client: AsyncClient, team: Team
) -> None:
    await _spaces(client, team)
    post = await _doc(client, team, "eng", "Solo un post")
    home = (await client.get(f"{API}/home", headers=team.member.headers)).json()
    assert home["featured"]["id"] == post and home["announcement"] is None


async def test_restricted_docs_never_reach_the_home(client: AsyncClient, team: Team) -> None:
    await _spaces(client, team)
    secret = await _doc(client, team, "eng", "Plan secreto", labels=["anuncio", "featured"])
    r = await client.put(
        f"{API}/nodes/{secret}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200, r.text
    r = await client.get(f"{API}/home", headers=team.member.headers)
    assert secret not in r.text and r.json()["spaces"][1]["docs"] == 0


async def test_no_folio_role_no_home(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    await db.execute(delete(FolioGlobalGrant))
    r = await client.get(f"{API}/home", headers=team.member.headers)
    assert r.status_code == 404 and "no access to Folio" in r.json()["detail"]
