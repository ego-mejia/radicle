"""The glossary (Folio 4.6): the AI suggests terms from Verified docs, a Folio admin
approves them, and readers only see approved terms, with a source they may open."""

import json

import httpx
import pytest
from httpx import AsyncClient

from radicle.platform.services import ai
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

ANSWER = json.dumps(
    [
        {
            "term": "Docket",
            "aliases": ["tickets"],
            "definition": "El tracker de Radicle.",
            "doc": 1,
        },
        {"term": "Folio", "definition": "Los docs de Radicle.", "doc": 9},
        {"term": "", "definition": "sin término"},
    ]
)


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": ANSWER}]})

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    return bodies


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


async def _ai(client: AsyncClient, team: Team) -> None:
    r = await client.put(
        "/api/v1/admin/ai",
        headers=team.instance.headers,
        json={"provider": "anthropic", "chat_model": "claude-sonnet-5-5", "api_key": "k"},
    )
    assert r.status_code == 200, r.text


async def test_acceptance_suggest_approve_and_read(
    client: AsyncClient, team: Team, llm: list[dict]
) -> None:
    i, m = team.instance.headers, team.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    verified = await _page(client, team, "Guía de Docket", verified=True)
    await _page(client, team, "Borrador suelto", verified=False)
    await _ai(client, team)

    r = await client.post(f"{API}/glossary/suggestions", headers=i)
    assert r.status_code == 201, r.text
    made = r.json()["items"]
    assert [t["term"] for t in made] == ["Docket", "Folio"]
    assert made[0]["status"] == "suggested" and made[0]["source"]["id"] == verified
    assert made[1]["source"] is None  # the AI pointed at a doc that wasn't sent
    sent = llm[0]["messages"][0]["content"]
    assert "Guía de Docket" in sent and "Borrador suelto" not in sent  # only Verified docs

    # Suggested terms aren't shown to readers.
    assert (await client.get(f"{API}/glossary", headers=m)).json()["items"] == []
    r = await client.patch(
        f"{API}/glossary/{made[0]['id']}", headers=i, json={"status": "approved"}
    )
    assert r.status_code == 200 and r.json()["status"] == "approved"
    await client.patch(f"{API}/glossary/{made[1]['id']}", headers=i, json={"status": "rejected"})
    items = (await client.get(f"{API}/glossary", headers=m)).json()["items"]
    assert [(t["term"], t["aliases"], t["source"]["title"]) for t in items] == [
        ("Docket", ["tickets"], "Guía de Docket")
    ]

    # Asking again only adds what's new.
    r = await client.post(f"{API}/glossary/suggestions", headers=i)
    assert r.json()["items"] == []
    pending = await client.get(f"{API}/glossary", params={"status": "rejected"}, headers=i)
    assert [t["term"] for t in pending.json()["items"]] == ["Folio"]


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


async def test_errors_and_permissions(client: AsyncClient, team: Team, llm: list[dict]) -> None:
    i, m = team.instance.headers, team.member.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    r = await client.post(f"{API}/glossary/suggestions", headers=i)
    assert r.status_code == 409 and "No AI provider" in r.json()["detail"]
    await _ai(client, team)
    r = await client.post(f"{API}/glossary/suggestions", headers=i)
    assert r.status_code == 422 and "no Verified docs" in r.json()["detail"]
    assert llm == []

    body = {"term": "Docket", "definition": "El tracker."}
    assert (await client.post(f"{API}/glossary", headers=m, json=body)).status_code == 403
    assert (await client.post(f"{API}/glossary/suggestions", headers=m)).status_code == 403
    r = await client.get(f"{API}/glossary", params={"status": "suggested"}, headers=m)
    assert r.status_code == 403
    tid = (await client.post(f"{API}/glossary", headers=i, json=body)).json()["id"]
    r = await client.patch(f"{API}/glossary/{tid}", headers=m, json={"status": "rejected"})
    assert r.status_code == 403
