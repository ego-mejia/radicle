"""Docket tickets inside docs over REST (Folio 4.1, 4.2)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team, new_ticket
from tests.integration.folio_helpers import API, publish
from tests.integration.test_restricted import restrict


@pytest.fixture
async def page(client: AsyncClient, board: Team) -> str:
    """PA-1 (assigned to luis) and PA-2 restricted; a published page that mentions both."""
    await new_ticket(client, board.admin, title="Conectar agentes", assignee="luis")
    await new_ticket(client, board.admin, title="SECRETO")
    r = await client.post(
        "/api/v1/projects/PA/security-levels",
        headers=board.admin.headers,
        json={"name": "Legal confidencial", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    assert (await restrict(client, board, "PA-2")).status_code == 200
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Guía"}
    )
    nid = r.json()["id"]
    await publish(client, board, nid, "# Conecta un agente\n\nVer PA-1 y PA-2.")
    return nid


async def test_previews_and_the_ticket_table(client: AsyncClient, board: Team, page: str) -> None:
    m = board.member.headers
    r = await client.get(f"{API}/tickets/preview", params={"keys": "pa-1, PA-2,ZZ-1"}, headers=m)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [(i["key"], i["restricted"]) for i in items] == [
        ("PA-1", False),
        ("PA-2", True),
        ("ZZ-1", True),
    ]
    one = items[0]["ticket"]
    assert one["assignee"]["handle"] == "luis" and one["url"] == "/t/PA-1"
    assert items[1]["ticket"] is None and "SECRETO" not in r.text
    r = await client.get(f"{API}/tickets/query", params={"rql": "project = PA"}, headers=m)
    assert [t["key"] for t in r.json()["items"]] == ["PA-1"] and r.json()["total"] == 1
    r = await client.get(f"{API}/tickets/query", params={"rql": "project = = PA"}, headers=m)
    assert r.status_code == 422
    many = ",".join(f"PA-{n}" for n in range(1, 102))
    r = await client.get(f"{API}/tickets/preview", params={"keys": many}, headers=m)
    assert r.status_code == 422 and "at most 100" in r.text


async def test_links_of_a_doc_and_docs_of_a_ticket(
    client: AsyncClient, board: Team, page: str
) -> None:
    i, m = board.instance.headers, board.member.headers
    r = await client.get(f"{API}/nodes/{page}/ticket-links", headers=m)
    links = r.json()["items"]
    assert sorted((lk["kind"], lk["restricted"]) for lk in links) == [
        ("mention", False),
        ("mention", True),
    ]
    assert "SECRETO" not in r.text and "PA-2" not in r.text
    r = await client.get(f"{API}/links", params={"ticket": "PA-1"}, headers=m)
    assert r.json()["items"][0]["node"]["id"] == page
    assert (await client.get(f"{API}/links?ticket=PA-2", headers=m)).status_code == 404

    body = {"key": "PA-1", "anchor": "conecta-un-agente"}
    r = await client.post(f"{API}/nodes/{page}/ticket-links", headers=i, json=body)
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["kind"] == "manual" and link["ticket"]["key"] == "PA-1"
    docs = (await client.get(f"{API}/links?ticket=PA-1", headers=m)).json()["items"]
    assert {d["url"].split("#")[-1] for d in docs} >= {"conecta-un-agente"}
    r = await client.post(f"{API}/nodes/{page}/ticket-links", headers=m, json=body)
    assert r.status_code == 403
    r = await client.delete(f"{API}/nodes/{page}/ticket-links/{link['id']}", headers=m)
    assert r.status_code == 403
    r = await client.delete(f"{API}/nodes/{page}/ticket-links/{link['id']}", headers=i)
    assert r.status_code == 204
    r = await client.delete(f"{API}/nodes/{page}/ticket-links/{link['id']}", headers=i)
    assert r.status_code == 404


async def test_create_a_ticket_from_a_selection(
    client: AsyncClient, board: Team, page: str
) -> None:
    body = {
        "text": "Documentar el token",
        "anchor": "conecta-un-agente",
        "project": "PA",
        "area": "Backend",
    }
    r = await client.post(f"{API}/nodes/{page}/tickets", headers=board.member.headers, json=body)
    assert r.status_code == 201, r.text
    made = r.json()
    assert made["kind"] == "created_from_text" and made["ticket"]["key"] == "PA-3"
    ticket = (await client.get("/api/v1/tickets/PA-3", headers=board.member.headers)).json()
    assert f"/folio/p/{page}-guia#conecta-un-agente" in ticket["description_md"]
    r = await client.post(f"{API}/nodes/{page}/tickets", headers=board.viewer.headers, json=body)
    assert r.status_code == 403
    r = await client.post(
        f"{API}/nodes/{page}/tickets", headers=board.member.headers, json={**body, "area": None}
    )
    assert r.status_code == 422
    r = await client.post(f"{API}/nodes/{page}/tickets", headers=board.outsider.headers, json=body)
    assert r.status_code in (403, 404)
