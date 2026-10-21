"""The glossary (Folio 4.6): Folio admins write and approve terms; readers only see approved
terms, with a source page only when they may open it."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


async def _page(client: AsyncClient, team: Team, title: str, *, verified: bool) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": title}
    )
    nid = r.json()["id"]
    await publish(client, team, nid, f"# {title}\n\nDocket es el tracker de Radicle.")
    if verified:
        r = await client.patch(f"{API}/nodes/{nid}/status", headers=i, json={"status": "verified"})
        assert r.status_code == 200, r.text
    return nid


async def test_admins_write_terms(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    nid = await _page(client, team, "RQL", verified=False)
    body = {"term": "RQL", "definition": "El lenguaje de consultas.", "source": nid}
    r = await client.post(f"{API}/glossary", headers=i, json=body)
    assert r.status_code == 201 and r.json()["status"] == "approved"
    tid = r.json()["id"]
    r = await client.post(f"{API}/glossary", headers=i, json={**body, "term": "rql"})
    assert r.status_code == 409 and "already in the glossary" in r.json()["detail"]
    r = await client.patch(
        f"{API}/glossary/{tid}", headers=i, json={"aliases": ["query", " query "], "source": None}
    )
    assert r.json()["aliases"] == ["query"] and r.json()["source"] is None
    r = await client.post(f"{API}/glossary", headers=i, json={"term": " ", "definition": "x"})
    assert r.status_code == 422 and "1 to 80" in r.json()["detail"]
    r = await client.post(
        f"{API}/glossary",
        headers=i,
        json={"term": "X", "definition": "y", "source": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 422
    # A reader who can't open the source page sees the term without it.
    r = await client.put(
        f"{API}/nodes/{nid}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200, r.text
    await client.patch(f"{API}/glossary/{tid}", headers=i, json={"source": nid})
    items = (await client.get(f"{API}/glossary", headers=team.member.headers)).json()["items"]
    assert items[0]["term"] == "RQL" and items[0]["source"] is None
    missing = f"{API}/glossary/00000000-0000-0000-0000-000000000000"
    assert (await client.patch(missing, headers=i, json={"status": "approved"})).status_code == 404


async def test_errors_and_permissions(client: AsyncClient, team: Team) -> None:
    i, m = team.instance.headers, team.member.headers

    body = {"term": "Docket", "definition": "El tracker."}
    assert (await client.post(f"{API}/glossary", headers=m, json=body)).status_code == 403
    r = await client.get(f"{API}/glossary", params={"status": "suggested"}, headers=m)
    assert r.status_code == 403
    tid = (await client.post(f"{API}/glossary", headers=i, json=body)).json()["id"]
    r = await client.patch(f"{API}/glossary/{tid}", headers=m, json={"status": "rejected"})
    assert r.status_code == 403
    # Only approved terms reach readers.
    await client.patch(f"{API}/glossary/{tid}", headers=i, json={"status": "rejected"})
    assert (await client.get(f"{API}/glossary", headers=m)).json()["items"] == []
