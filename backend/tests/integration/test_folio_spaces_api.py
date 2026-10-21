"""Folio spaces and the tree over REST (Folio 1.1): happy paths, errors and permissions."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team

API = "/api/v1/folio"


@pytest.fixture
async def space(client: AsyncClient, team: Team) -> dict:
    r = await client.post(
        f"{API}/spaces",
        headers=team.instance.headers,
        json={"key": "ai-tools", "name": "AI Tools", "icon": "bot"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _node(client: AsyncClient, team: Team, **body: object) -> dict:
    r = await client.post(
        f"{API}/nodes", headers=team.instance.headers, json={"space": "ai-tools", **body}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_build_and_read_the_tree(client: AsyncClient, team: Team, space: dict) -> None:
    folder = await _node(client, team, kind="folder", title="Get Started")
    page = await _node(client, team, kind="page", title="Bienvenido", parent=folder["id"])
    child = await _node(client, team, kind="page", title="Conecta un agente", parent=page["id"])
    post = await _node(client, team, kind="blog_post", title="Novedades")
    reader = team.member.headers

    r = await client.get(f"{API}/spaces/ai-tools/tree", headers=reader)
    assert r.status_code == 200
    [root] = r.json()
    assert (root["title"], root["kind"]) == ("Get Started", "folder")
    assert root["children"][0]["children"][0]["id"] == child["id"]

    r = await client.get(f"{API}/nodes/{child['id']}", headers=reader)
    body = r.json()
    assert body["space"] == "ai-tools" and body["slug"] == "conecta-un-agente"
    assert [b["title"] for b in body["breadcrumbs"]] == ["Get Started", "Bienvenido"]

    r = await client.get(f"{API}/spaces/ai-tools/posts", headers=reader)
    assert [p["id"] for p in r.json()["items"]] == [post["id"]]
    assert [
        s["key"] for s in (await client.get(f"{API}/spaces", headers=reader)).json()["items"]
    ] == ["ai-tools"]


async def test_edit_move_and_delete(client: AsyncClient, team: Team, space: dict) -> None:
    i = team.instance.headers
    a = await _node(client, team, kind="page", title="A")
    b = await _node(client, team, kind="page", title="B")
    r = await client.patch(f"{API}/nodes/{b['id']}", headers=i, json={"title": "Be", "icon": None})
    assert r.json()["title"] == "Be" and r.json()["slug"] == "be"
    r = await client.post(f"{API}/nodes/{b['id']}/move", headers=i, json={"before": a["id"]})
    assert r.status_code == 200
    tree = (await client.get(f"{API}/spaces/ai-tools/tree", headers=i)).json()
    assert [n["title"] for n in tree] == ["Be", "A"]
    r = await client.post(f"{API}/nodes/{a['id']}/move", headers=i, json={"parent": b["id"]})
    assert r.json()["parent_id"] == b["id"]

    assert (await client.delete(f"{API}/nodes/{b['id']}", headers=i)).status_code == 204
    assert (await client.get(f"{API}/nodes/{a['id']}", headers=i)).status_code == 404

    r = await client.patch(
        f"{API}/spaces/ai-tools", headers=i, json={"name": "AI", "description": "Agentes"}
    )
    assert r.json()["name"] == "AI" and r.json()["icon"] == "bot"
    assert (await client.delete(f"{API}/spaces/ai-tools", headers=i)).status_code == 204
    assert (await client.get(f"{API}/spaces/ai-tools", headers=i)).status_code == 404


async def test_personal_space(client: AsyncClient, team: Team) -> None:
    r = await client.get(f"{API}/me/personal-space", headers=team.member.headers)
    assert r.status_code == 200 and r.json() | {"created_at": None} == r.json() | {
        "key": "me-luis",
        "kind": "personal",
        "created_at": None,
    }
    other = await client.get(f"{API}/spaces/me-luis", headers=team.viewer.headers)
    assert other.status_code == 404


async def test_actionable_errors(client: AsyncClient, team: Team, space: dict) -> None:
    i = team.instance.headers
    r = await client.post(f"{API}/spaces", headers=i, json={"key": "AI Tools", "name": "X"})
    assert r.status_code == 422 and "ai-tools" in r.json()["detail"]
    r = await client.post(f"{API}/spaces", headers=i, json={"key": "ai-tools", "name": "X"})
    assert r.status_code == 409
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "nope", "kind": "page", "title": "X"}
    )
    assert r.status_code == 404 and "lists the ones you can see" in r.json()["detail"]
    post = await _node(client, team, kind="blog_post", title="P")
    r = await client.post(
        f"{API}/nodes",
        headers=i,
        json={"space": "ai-tools", "kind": "page", "title": "X", "parent": post["id"]},
    )
    assert r.status_code == 422 and "cannot have children" in r.json()["detail"]
    page = await _node(client, team, kind="page", title="P")
    r = await client.post(f"{API}/nodes/{page['id']}/move", headers=i, json={"parent": page["id"]})
    assert r.status_code == 422 and "under itself" in r.json()["detail"]
    r = await client.get(f"{API}/nodes/00000000-0000-0000-0000-000000000000", headers=i)
    assert r.status_code == 404


async def test_readers_read_but_do_not_write(client: AsyncClient, team: Team, space: dict) -> None:
    page = await _node(client, team, kind="page", title="Solo lectura")
    reader = team.member.headers
    assert (await client.get(f"{API}/nodes/{page['id']}", headers=reader)).status_code == 200
    r = await client.post(f"{API}/spaces", headers=reader, json={"key": "mine", "name": "Mío"})
    assert r.status_code == 403 and "creator" in r.json()["detail"]
    r = await client.post(
        f"{API}/nodes", headers=reader, json={"space": "ai-tools", "kind": "page", "title": "X"}
    )
    assert r.status_code == 403
    assert (await client.delete(f"{API}/nodes/{page['id']}", headers=reader)).status_code == 403
    r = await client.patch(f"{API}/spaces/ai-tools", headers=reader, json={"name": "X"})
    assert r.status_code == 403
    anonymous = AsyncClient(transport=client._transport, base_url="http://test")
    assert (await anonymous.get(f"{API}/spaces")).status_code == 401
