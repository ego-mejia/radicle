"""The "list by label" block (Folio 3.4): published pages with the label, as the reader sees."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


async def _page(client: AsyncClient, team: Team, space: str, title: str) -> str:
    r = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": space, "kind": "page", "title": title},
    )
    return str(r.json()["id"])


async def test_lists_published_pages_you_can_see(client: AsyncClient, team: Team) -> None:
    i, m = team.instance.headers, team.member.headers
    for key in ("docs", "ops"):
        await client.post(f"{API}/spaces", headers=i, json={"key": key, "name": key})
    first = await _page(client, team, "docs", "Primera")
    second = await _page(client, team, "ops", "Segunda")
    draft = await _page(client, team, "docs", "Borrador")  # never published
    secret = await _page(client, team, "docs", "Secreta")
    for node in (first, second, secret):
        await publish(client, team, node)  # labels: mcp, agentes
    await client.put(
        f"{API}/nodes/{secret}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    r = await client.get(f"{API}/page-list", params={"label": "#MCP"}, headers=m)
    assert r.status_code == 200, r.text
    assert [p["title"] for p in r.json()["items"]] == ["Segunda", "Primera"]  # newest first
    assert r.json()["items"][0]["space"] == "ops"
    r = await client.get(f"{API}/page-list", params={"label": "mcp", "space": "docs"}, headers=m)
    assert [p["id"] for p in r.json()["items"]] == [first]
    r = await client.get(f"{API}/page-list", params={"label": "mcp", "limit": 1}, headers=m)
    assert len(r.json()["items"]) == 1
    r = await client.get(f"{API}/page-list", params={"label": "mcp"}, headers=i)
    assert secret in [p["id"] for p in r.json()["items"]] and draft not in str(r.json())


async def test_errors(client: AsyncClient, team: Team) -> None:
    m = team.member.headers
    r = await client.get(f"{API}/page-list", params={"label": "#"}, headers=m)
    assert r.status_code == 422 and "label" in r.json()["detail"]
    r = await client.get(f"{API}/page-list", params={"label": "x", "limit": 99}, headers=m)
    assert r.status_code == 422
    client.cookies.clear()
    assert (await client.get(f"{API}/page-list", params={"label": "x"})).status_code == 401
