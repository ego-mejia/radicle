"""Folio's events over webhooks (Folio 5.5). Acceptance: a receiver gets `page.published`
with a valid signature."""

import json
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import quality
from radicle.platform.services import safe_fetch, webhooks
from tests.conftest import Clock, Team, run_jobs
from tests.integration.folio_helpers import API, agent_can_write, agent_submits, publish


@pytest.fixture
def received(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    got: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        got.append(request)
        return httpx.Response(200)

    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return got


async def _hook(client: AsyncClient, team: Team, **body: Any) -> str:
    base = {"name": "CI", "url": "https://93.184.216.34/radicle"}
    r = await client.post("/api/v1/webhooks", headers=team.instance.headers, json=base | body)
    assert r.status_code == 201, r.text
    return str(r.json()["secret"])


async def _page(client: AsyncClient, team: Team, title: str = "Deploy") -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
    )
    return str(r.json()["id"])


def _events(received: list[httpx.Request]) -> list[tuple[str, dict[str, Any]]]:
    docs = [json.loads(r.content) for r in received]
    return [(d["event"], d["data"]) for d in docs]


async def test_acceptance_a_receiver_gets_page_published_signed(
    client: AsyncClient, db: AsyncSession, team: Team, received: list[httpx.Request]
) -> None:
    secret = await _hook(client, team, events=["page.published"])
    page = await _page(client, team)
    await publish(client, team, page)
    await run_jobs(db)
    [request] = received
    assert webhooks.verify(secret, request.headers["radicle-signature"], request.content)
    [(name, data)] = _events(received)
    assert name == "page.published" and data["version"] == 1
    assert data["page"]["id"] == page and data["page"]["space"] == "docs"
    assert data["page"]["url"].endswith(f"/folio/p/{page}-deploy")
    assert data["actor"] == team.instance.handle and "content" not in json.dumps(data)


async def test_every_folio_event(
    client: AsyncClient, db: AsyncSession, team: Team, received: list[httpx.Request], clock: Clock
) -> None:
    await _hook(client, team, filter={"space": "docs"})
    i = team.instance.headers
    page = await _page(client, team)
    await publish(client, team, page)
    await publish(client, team, page, md="Hola de nuevo")
    await client.post(f"{API}/nodes/{page}/comments", headers=i, json={"body": "¿Vigente?"})
    await client.patch(f"{API}/nodes/{page}/status", headers=i, json={"status": "verified"})
    await agent_can_write(client, team, "docs")
    sent = await agent_submits(client, team, "docs", "Cambios")
    await client.post(f"{API}/submissions/{sent['id']}/reject", headers=i, json={"comment": "No"})
    await run_jobs(db)
    clock.advance(days=91)
    await quality.outdate_expired(db)
    clock.advance(days=-91)
    await client.post(f"{API}/nodes/{page}/archive", headers=i)
    await run_jobs(db)
    names = [name for name, _ in _events(received)]
    assert names == [
        "page.published",
        "page.updated",
        "page.commented",
        "page.status_changed",
        "submission.created",
        "submission.decided",
        "page.outdated",
        "page.status_changed",
        "page.archived",
    ]
    by_name = dict(_events(received))
    assert by_name["submission.decided"]["decision"] == "rejected"
    assert by_name["page.status_changed"]["after"] == "outdated"


async def test_a_space_filter_keeps_other_spaces_out(
    client: AsyncClient, db: AsyncSession, team: Team, received: list[httpx.Request]
) -> None:
    await _hook(client, team, filter={"space": "ops"})
    await publish(client, team, await _page(client, team))
    await run_jobs(db)
    assert received == []
