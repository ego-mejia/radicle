"""Comments over REST (Folio 2.3)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

MD = "# Agentes\n\nCrea el agente en Admin y conéctalo por MCP con su token.\n\nFin."


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    grants = [
        {"grantee_type": "everyone", "permissions": ["view", "comment"]},
        {"grantee_type": "user", "grantee": team.instance.handle, "permissions": ["admin"]},
    ]
    await client.put(f"{API}/spaces/docs/grants", headers=i, json={"grants": grants})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    await publish(client, team, r.json()["id"], md=MD)
    return str(r.json()["id"])


async def test_threads_end_to_end(client: AsyncClient, team: Team, page: str) -> None:
    m, a = team.member.headers, team.admin.headers
    url = f"{API}/nodes/{page}/comments"
    r = await client.post(url, headers=m, json={"body": "¿Sigue vigente?"})
    assert r.status_code == 201, r.text
    footer = r.json()
    assert footer["kind"] == "footer" and footer["anchor"] is None
    assert footer["comments"][0]["author"] == "luis" and footer["comments"][0]["mine"]

    r = await client.post(url, headers=m, json={"body": "¿Y el token?", "quote": "por MCP"})
    inline = r.json()
    assert inline["kind"] == "inline" and inline["anchor"]["quote"] == "por MCP"
    anchor = {
        "quote": "conéctalo por MCP",
        "prefix": "Crea el agente en Admin y ",
        "suffix": " con su token.",
    }
    r = await client.post(url, headers=a, json={"body": "Con anchor", "anchor": anchor})
    assert r.status_code == 201 and r.json()["anchor"]["quote"] == "conéctalo por MCP"

    r = await client.post(url, headers=a, json={"body": "Sí.", "thread_id": footer["id"]})
    assert [c["body_md"] for c in r.json()["comments"]] == ["¿Sigue vigente?", "Sí."]
    reply = r.json()["comments"][1]
    assert reply["author"] == "ana" and reply["mine"]

    r = await client.patch(
        f"{API}/comments/{reply['id']}", headers=a, json={"body": "Sí, desde ayer."}
    )
    assert r.json()["comments"][1]["body_md"] == "Sí, desde ayer."
    assert r.json()["comments"][1]["edited_at"] is not None

    r = await client.post(f"{API}/comments/{reply['id']}/resolve", headers=m)
    assert r.json()["resolved_by"] == "luis"
    listed = (await client.get(url, headers=m)).json()["items"]
    assert footer["id"] not in [t["id"] for t in listed] and len(listed) == 2
    listed = (await client.get(url, params={"include_resolved": True}, headers=m)).json()
    assert len(listed["items"]) == 3
    r = await client.post(f"{API}/comments/{footer['id']}/reopen", headers=m)
    assert r.json()["resolved_at"] is None

    assert (await client.delete(f"{API}/comments/{reply['id']}", headers=a)).status_code == 204
    thread = next(
        t for t in (await client.get(url, headers=m)).json()["items"] if t["id"] == footer["id"]
    )
    assert len(thread["comments"]) == 1


async def test_errors(client: AsyncClient, team: Team, page: str) -> None:
    m, a = team.member.headers, team.admin.headers
    url = f"{API}/nodes/{page}/comments"
    r = await client.post(url, headers=m, json={"body": "x", "quote": "no está"})
    assert r.status_code == 422 and "not in the page" in r.json()["detail"]
    r = await client.post(url, headers=m, json={"body": " "})
    assert r.status_code == 422
    mine = (await client.post(url, headers=m, json={"body": "Mío"})).json()
    cid = mine["comments"][0]["id"]
    r = await client.patch(f"{API}/comments/{cid}", headers=a, json={"body": "Ajeno"})
    assert r.status_code == 403
    await client.post(f"{API}/comments/{cid}/resolve", headers=m)
    r = await client.post(url, headers=a, json={"body": "Tarde", "thread_id": mine["id"]})
    assert r.status_code == 409 and "Reopen" in r.json()["detail"]
    r = await client.patch(
        f"{API}/comments/00000000-0000-0000-0000-000000000000", headers=m, json={"body": "x"}
    )
    assert r.status_code == 404


async def test_permissions(client: AsyncClient, team: Team, page: str) -> None:
    i, m = team.instance.headers, team.member.headers
    url = f"{API}/nodes/{page}/comments"
    created = (await client.post(url, headers=m, json={"body": "Hola"})).json()
    grants = [
        {"grantee_type": "everyone", "permissions": ["view"]},
        {"grantee_type": "user", "grantee": team.instance.handle, "permissions": ["admin"]},
    ]
    await client.put(f"{API}/spaces/docs/grants", headers=i, json={"grants": grants})
    r = await client.post(url, headers=m, json={"body": "¿Puedo?"})
    assert r.status_code == 403 and "comment permission" in r.json()["detail"]
    assert (await client.get(url, headers=m)).status_code == 200  # reading is still fine
    body = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    await client.put(f"{API}/nodes/{page}/restrictions", headers=i, json=body)
    assert (await client.get(url, headers=m)).status_code == 404
    cid = created["comments"][0]["id"]
    assert (await client.post(f"{API}/comments/{cid}/resolve", headers=m)).status_code == 404
