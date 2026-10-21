"""Searching Folio (Folio 1.6): text, semantic and hybrid, filters, and visibility."""

import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, METADATA

GUIDE = (
    "Todo sobre agentes en Radicle.\n\n# Antes de empezar\n\nNecesitas ser admin.\n\n"
    "# Conecta un agente\n\nCrea un agente en Admin y conéctalo por MCP con su token.\n"
)
DEPLOY = "# Despliegue\n\nCómo subir Radicle a producción con Docker.\n"


async def _page(client: AsyncClient, team: Team, title: str, md: str, **meta: object) -> str:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
    )
    nid = r.json()["id"]
    await client.put(
        f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": md, "metadata": METADATA | meta}
    )
    assert (await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})).status_code == 201
    return nid


@pytest.fixture
async def docs(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    guide = await _page(client, team, "Conecta un agente a Radicle", GUIDE)
    deploy = await _page(client, team, "Guía de deploy", DEPLOY, doc_type="guide", labels=["ops"])
    await run_jobs(db)
    return {"guide": guide, "deploy": deploy}


async def test_acceptance_the_right_guide_at_the_right_section(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    r = await client.get(
        f"{API}/search", params={"q": "cómo conecto un agente"}, headers=team.member.headers
    )
    assert r.status_code == 200, r.text
    first = r.json()["items"][0]
    assert first["node_id"] == docs["guide"] and first["section"] == ["Conecta un agente"]
    assert first["url"].endswith("#conecta-un-agente") and "**" in first["snippet"]
    assert first["matched_by"] == ["text"]  # no AI provider: hybrid falls back to text


async def test_a_title_that_is_also_a_heading_lands_on_the_section(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await client.post(
        f"{API}/spaces", headers=team.instance.headers, json={"key": "docs", "name": "Docs"}
    )
    md = "Intro.\n\n# Conecta un agente\n\nCrea el agente en Admin y usa su token por MCP.\n"
    nid = await _page(client, team, "Conecta un agente", md)
    await run_jobs(db)
    params = {"q": "cómo conecto un agente"}
    r = await client.get(f"{API}/search", params=params, headers=team.member.headers)
    first = r.json()["items"][0]
    assert first["node_id"] == nid and first["section"] == ["Conecta un agente"]


async def test_a_question_finds_pages_with_some_of_its_words(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await client.post(
        f"{API}/spaces", headers=team.instance.headers, json={"key": "docs", "name": "Docs"}
    )
    nid = await _page(
        client,
        team,
        "Conecta un agente",
        "# Crea el agente\n\nConéctalo con su token.\n",
        description="Pasos para enlazar un agente por MCP con su token y sus permisos.",
    )
    await run_jobs(db)
    h = team.member.headers
    for q in ("cómo conecto un agente", "¿cómo conecto mi agente a Radicle?"):
        r = await client.get(f"{API}/search", params={"q": q, "mode": "text"}, headers=h)
        assert [x["node_id"] for x in r.json()["items"]][:1] == [nid], q
    # Exclusions keep their meaning: no fallback that would match everything.
    r = await client.get(f"{API}/search", params={"q": "agente -token", "mode": "text"}, headers=h)
    assert r.json()["items"] == []


async def test_snippets_hide_markdown(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    await client.post(
        f"{API}/spaces", headers=team.instance.headers, json={"key": "docs", "name": "Docs"}
    )
    md = (
        "# Agentes\n\nVe a **Admin → Agentes** y usa `agente-docs`.\n\n"
        "| Campo | Valor |\n|---|---|\n| handle | bot |\n"
    )
    await _page(client, team, "Agentes", md)
    await run_jobs(db)
    params = {"q": "agentes", "mode": "text"}
    r = await client.get(f"{API}/search", params=params, headers=team.member.headers)
    snippet = r.json()["items"][0]["snippet"]
    assert "**Agentes**" in snippet and "`" not in snippet and "|" not in snippet
    assert snippet.count("**") % 2 == 0 and "***" not in snippet


async def test_filters(client: AsyncClient, team: Team, docs: dict) -> None:
    async def ids(**params: str) -> list[str]:
        r = await client.get(
            f"{API}/search", params={"q": "radicle", **params}, headers=team.member.headers
        )
        return [h["node_id"] for h in r.json()["items"]]

    assert set(await ids()) == {docs["guide"], docs["deploy"]}
    assert await ids(doc_type="guide") == [docs["deploy"]]
    assert await ids(label="#ops") == [docs["deploy"]]
    assert await ids(owner="@Fernando", mode="text") != []
    assert await ids(space="otro") == []
    assert await ids(language="en") == []


async def test_semantic_and_hybrid_with_a_provider(
    client: AsyncClient, db: AsyncSession, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    def vector(text: str) -> list[float]:
        return [1.0, 0.0] if "despliegue" in text.lower() or "subir" in text.lower() else [0.0, 1.0]

    def handler(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        inputs = [inputs] if isinstance(inputs, str) else inputs
        return httpx.Response(
            200, json={"data": [{"index": n, "embedding": vector(t)} for n, t in enumerate(inputs)]}
        )

    from radicle.platform.services import ai

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    await client.put(
        "/api/v1/admin/ai",
        headers=team.instance.headers,
        json={"provider": "openai", "embedding_model": "m", "api_key": "k"},
    )
    await client.post(
        f"{API}/spaces", headers=team.instance.headers, json={"key": "docs", "name": "Docs"}
    )
    await _page(client, team, "Conecta un agente", GUIDE)
    deploy = await _page(client, team, "Guía de deploy", DEPLOY)
    await run_jobs(db)

    r = await client.get(
        f"{API}/search",
        params={"q": "subir a producción", "mode": "semantic"},
        headers=team.member.headers,
    )
    assert r.json()["items"][0]["node_id"] == deploy
    assert r.json()["items"][0]["matched_by"] == ["semantic"]
    r = await client.get(
        f"{API}/search", params={"q": "despliegue docker"}, headers=team.member.headers
    )
    top = r.json()["items"][0]
    assert top["node_id"] == deploy and sorted(top["matched_by"]) == ["semantic", "text"]


async def test_hybrid_survives_a_provider_that_fails(
    client: AsyncClient, team: Team, docs: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from radicle.platform.services import ai

    await client.put(
        "/api/v1/admin/ai",
        headers=team.instance.headers,
        json={"provider": "openai", "embedding_model": "m", "api_key": "k"},
    )
    monkeypatch.setattr(ai, "transport", httpx.MockTransport(lambda r: httpx.Response(500)))
    params = {"q": "conecta agente"}
    r = await client.get(f"{API}/search", params=params, headers=team.member.headers)
    assert r.status_code == 200 and r.json()["items"][0]["matched_by"] == ["text"]
    params["mode"] = "semantic"
    r = await client.get(f"{API}/search", params=params, headers=team.member.headers)
    assert r.status_code >= 400 and "500" in r.json()["detail"]


async def test_semantic_without_a_provider_says_how(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    r = await client.get(
        f"{API}/search", params={"q": "x", "mode": "semantic"}, headers=team.member.headers
    )
    assert r.status_code == 422 and "AI provider" in r.json()["detail"]
    r = await client.get(f"{API}/search", params={"q": ""}, headers=team.member.headers)
    assert r.status_code == 422


async def test_restricted_pages_never_show_up(
    client: AsyncClient, db: AsyncSession, team: Team, docs: dict
) -> None:
    r = await client.put(
        f"{API}/nodes/{docs['guide']}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": "fernando"}]},
    )
    assert r.status_code == 200
    await run_jobs(db)
    r = await client.get(
        f"{API}/search", params={"q": "conecta agente"}, headers=team.member.headers
    )
    assert docs["guide"] not in [h["node_id"] for h in r.json()["items"]]
    r = await client.get(
        f"{API}/search", params={"q": "conecta agente"}, headers=team.instance.headers
    )
    assert r.json()["items"][0]["node_id"] == docs["guide"]
