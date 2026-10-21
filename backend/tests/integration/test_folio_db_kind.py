"""The database node kind (Folio 3.6): created like any node, read as it is, never
published and without a draft."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API


async def test_a_database_node(client: AsyncClient, team: Team) -> None:
    i, m = team.instance.headers, team.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "database", "title": "Inventario"}
    )
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    tree = (await client.get(f"{API}/spaces/docs/tree", headers=m)).json()
    assert [(n["title"], n["kind"]) for n in tree] == [("Inventario", "database")]
    assert (await client.get(f"{API}/nodes/{nid}", headers=m)).status_code == 200
    found = await client.get(f"{API}/nodes", params={"q": "kind = database"}, headers=m)
    assert [d["id"] for d in found.json()["items"]] == [nid]
    r = await client.get(f"{API}/nodes/{nid}/draft", headers=i)
    assert r.status_code == 422 and "rows, not a draft" in r.json()["detail"]
    r = await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})
    assert r.status_code == 422 and "aren't published" in r.json()["detail"]
