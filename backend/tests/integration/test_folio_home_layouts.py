"""The home editor over REST (Folio 3.2): draft, publish, history and restore."""

from httpx import AsyncClient

from radicle.folio.services.home_layouts import DEFAULT
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

URL = f"{API}/admin/home"


def _block(id: str, type: str, y: int = 0, w: int = 4, **config: object) -> dict:
    return {"id": id, "type": type, "x": 0, "y": y, "w": w, "h": 2, "config": config}


async def test_edit_publish_and_restore(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.get(f"{URL}/draft", headers=i)
    assert r.status_code == 200 and r.json()["saved"] is False
    assert r.json()["layout"]["blocks"] == DEFAULT["blocks"]

    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    body = {"space": "docs", "kind": "blog_post", "title": "Hola"}
    node = (await client.post(f"{API}/nodes", headers=i, json=body)).json()
    await publish(client, team, node["id"])
    first = {
        "columns": 12,
        "blocks": [
            _block("hero", "featured", w=8, node=node["id"]),
            _block("q", "query", y=2, rql="space = docs", limit=3),
            _block("txt", "text", y=4, w=12, markdown="**Bienvenidos**"),
        ],
    }
    r = await client.put(f"{URL}/draft", headers=i, json=first)
    assert r.status_code == 200 and r.json()["saved"] is True, r.text
    r = await client.post(f"{URL}/publish", headers=i)
    assert r.status_code == 201, r.text
    first_id = r.json()["id"]
    assert r.json()["is_active"] and r.json()["published_by"] == team.instance.handle
    assert (await client.post(f"{URL}/publish", headers=i)).status_code == 409

    await client.put(f"{URL}/draft", headers=i, json={"blocks": first["blocks"][:1]})
    await client.post(f"{URL}/publish", headers=i)
    history = (await client.get(f"{URL}/history", headers=i)).json()["items"]
    assert [len(h["layout"]["blocks"]) for h in history] == [1, 3]
    r = await client.post(f"{URL}/history/{first_id}/restore", headers=i)
    assert r.status_code == 201 and len(r.json()["layout"]["blocks"]) == 3
    r = await client.post(f"{URL}/history/{node['id']}/restore", headers=i)
    assert r.status_code == 404


async def test_errors_name_the_block(client: AsyncClient, team: Team) -> None:
    layout = {"blocks": [_block("q", "query", rql="spaec = docs")]}
    r = await client.put(f"{URL}/draft", headers=team.instance.headers, json=layout)
    assert r.status_code == 422
    error = r.json()["errors"][0]
    assert error["field"] == "blocks[0].config.rql" and error["position"] == 0


async def test_only_folio_admins(client: AsyncClient, team: Team) -> None:
    m = team.member.headers
    assert (await client.get(f"{URL}/draft", headers=m)).status_code == 403
    r = await client.put(f"{URL}/draft", headers=m, json={"blocks": []})
    assert r.status_code == 403
    assert (await client.post(f"{URL}/publish", headers=m)).status_code == 403
    assert (await client.get(f"{URL}/history", headers=m)).status_code == 403
