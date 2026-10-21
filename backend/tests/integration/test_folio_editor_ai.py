"""AI in the editor (Folio 4.6): summarize, rewrite and suggest metadata as proposals that
never change the page; off without a provider, for Folio or in the space."""

import json

import httpx
import pytest
from httpx import AsyncClient

from radicle.platform.services import ai
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

PAGE = "# Conectar un agente\n\nCrea el agente en Admin y conéctalo con su token por MCP."


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """A fake Anthropic: answers what the test queues, and records each request body."""
    bodies: list[dict] = []
    answers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        text = answers.pop(0) if answers else "- Un resumen."
        return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    bodies.append({"answers": answers})  # bodies[0] holds the queue
    return bodies


async def _setup(client: AsyncClient, team: Team, *, provider: bool = True) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Guía MCP"}
    )
    nid = r.json()["id"]
    await publish(client, team, nid, PAGE)
    if provider:
        r = await client.put(
            "/api/v1/admin/ai",
            headers=i,
            json={"provider": "anthropic", "chat_model": "claude-sonnet-5-5", "api_key": "k"},
        )
        assert r.status_code == 200, r.text
    return nid


async def test_summarize_and_rewrite_are_proposals(
    client: AsyncClient, team: Team, llm: list[dict]
) -> None:
    i = team.instance.headers
    nid = await _setup(client, team)
    r = await client.get(f"{API}/ai/availability", params={"space": "eng"}, headers=i)
    assert r.json() == {"available": True, "reason": None, "message": None}

    r = await client.post(f"{API}/ai/summarize", headers=i, json={"node_id": nid})
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == "- Un resumen."
    assert "Crea el agente en Admin" in llm[1]["messages"][0]["content"]

    llm[0]["answers"].append("Create the agent in Admin.")
    body = {"node_id": nid, "text": "Crea el agente en Admin.", "mode": "translate"}
    r = await client.post(f"{API}/ai/rewrite", headers=i, json=body)
    assert r.status_code == 422 and "language" in r.text
    for text, error in (("  ", "Select the text"), ("x" * 8001, "at most 8000")):
        r = await client.post(f"{API}/ai/rewrite", headers=i, json={**body, "text": text})
        assert r.status_code == 422 and error in r.json()["detail"]
    r = await client.post(f"{API}/ai/rewrite", headers=i, json={**body, "language": "English"})
    assert r.json()["text"] == "Create the agent in Admin."
    assert "English" in llm[2]["system"]
    draft = (await client.get(f"{API}/nodes/{nid}/draft", headers=i)).json()
    assert draft["content_md"].strip() == PAGE  # nothing applied by itself


async def test_suggest_metadata_keeps_only_what_publishing_accepts(
    client: AsyncClient, team: Team, llm: list[dict]
) -> None:
    i = team.instance.headers
    nid = await _setup(client, team)
    llm[0]["answers"].append(
        'Aquí va: {"description": "Cómo crear un agente en Admin y conectarlo a Radicle por '
        'MCP con su token.", "labels": ["MCP", "#agentes", "no válido!"], '
        '"doc_type": "how-to"}'
    )
    r = await client.post(f"{API}/ai/suggest-metadata", headers=i, json={"node_id": nid})
    assert r.status_code == 200, r.text
    assert r.json()["labels"] == ["mcp", "agentes"] and r.json()["doc_type"] == "how-to"
    assert r.json()["description"].startswith("Cómo crear un agente")
    assert "mcp" in llm[1]["messages"][0]["content"]  # labels in use go in the prompt

    llm[0]["answers"].append('{"description": "corta", "labels": [], "doc_type": "novela"}')
    r = await client.post(f"{API}/ai/suggest-metadata", headers=i, json={"node_id": nid})
    assert r.json() == {"description": None, "labels": [], "doc_type": None}

    llm[0]["answers"].append("No sé.")
    r = await client.post(f"{API}/ai/suggest-metadata", headers=i, json={"node_id": nid})
    assert r.status_code == 502 and "suggestions" in r.json()["detail"]


async def test_off_without_provider_for_folio_or_in_the_space(
    client: AsyncClient, team: Team, llm: list[dict]
) -> None:
    i = team.instance.headers
    nid = await _setup(client, team, provider=False)
    r = await client.get(f"{API}/ai/availability", params={"space": "eng"}, headers=i)
    assert r.json()["available"] is False and r.json()["reason"] == "no_provider"
    r = await client.post(f"{API}/ai/summarize", headers=i, json={"node_id": nid})
    assert r.status_code == 409 and "Admin, AI provider" in r.json()["detail"]

    await client.put(
        "/api/v1/admin/ai",
        headers=i,
        json={"provider": "anthropic", "chat_model": "m", "features": {"folio_editor": False}},
    )
    r = await client.get(f"{API}/ai/availability", params={"space": "eng"}, headers=i)
    assert r.json()["reason"] == "off_for_folio"

    await client.put("/api/v1/admin/ai", headers=i, json={"features": {}})
    r = await client.patch(f"{API}/spaces/eng", headers=i, json={"ai_enabled": False})
    assert r.status_code == 200 and r.json()["ai_enabled"] is False
    r = await client.get(f"{API}/ai/availability", params={"space": "eng"}, headers=i)
    assert r.json()["reason"] == "off_in_space"
    r = await client.post(f"{API}/ai/summarize", headers=i, json={"node_id": nid})
    assert r.status_code == 409 and "space settings" in r.json()["detail"]
    assert len(llm) == 1  # the provider was never called


async def test_permissions(client: AsyncClient, team: Team, llm: list[dict]) -> None:
    nid = await _setup(client, team)
    m = team.member.headers
    # A reader may summarize what they can read, but not rewrite or suggest metadata.
    r = await client.post(f"{API}/ai/summarize", headers=m, json={"node_id": nid})
    assert r.status_code == 200, r.text
    body = {"node_id": nid, "text": "Hola", "mode": "clearer"}
    assert (await client.post(f"{API}/ai/rewrite", headers=m, json=body)).status_code == 403
    r = await client.post(f"{API}/ai/suggest-metadata", headers=m, json={"node_id": nid})
    assert r.status_code == 403
    r = await client.patch(f"{API}/spaces/eng", headers=m, json={"ai_enabled": False})
    assert r.status_code == 403
    missing = {"node_id": "00000000-0000-0000-0000-000000000000"}
    r = await client.post(f"{API}/ai/summarize", headers=m, json=missing)
    assert r.status_code == 404
