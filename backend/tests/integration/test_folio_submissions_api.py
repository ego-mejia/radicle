"""The approval queue over REST (Folio 1.5)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditEntry
from tests.conftest import Team
from tests.integration.folio_helpers import API, agent_can_write, agent_submits


@pytest.fixture
async def space(client: AsyncClient, team: Team) -> str:
    r = await client.post(
        f"{API}/spaces", headers=team.instance.headers, json={"key": "docs", "name": "Docs"}
    )
    assert r.status_code == 201
    await agent_can_write(client, team, "docs")
    return "docs"


async def test_acceptance_agent_post_is_approved_from_the_queue(
    client: AsyncClient, db: AsyncSession, team: Team, space: str
) -> None:
    submission = await agent_submits(client, team, space, "Cambios de la semana")
    assert submission["status"] == "pending" and submission["submitted_by"] == "agent-backend"
    i = team.instance.headers
    queue = (await client.get(f"{API}/submissions", params={"status": "pending"}, headers=i)).json()
    assert [s["id"] for s in queue["items"]] == [submission["id"]]

    detail = (await client.get(f"{API}/submissions/{submission['id']}", headers=i)).json()
    assert detail["current_version"] is None and detail["content_md"] == "# Cambios\n"
    assert [b["op"] for b in detail["blocks"]] == ["added"]
    hidden = await client.get(f"{API}/nodes/{submission['node_id']}", headers=team.member.headers)
    assert hidden.status_code == 404

    r = await client.post(f"{API}/submissions/{submission['id']}/approve", headers=i, json={})
    assert r.status_code == 201, r.text
    assert (r.json()["number"], r.json()["author"], r.json()["approved_by"]) == (
        1,
        "agent-backend",
        "fernando",
    )
    shown = await client.get(f"{API}/nodes/{submission['node_id']}", headers=team.member.headers)
    assert shown.status_code == 200 and shown.json()["version"] == 1
    entry = await db.scalar(
        select(AuditEntry).where(AuditEntry.action == "folio.submission_approve")
    )
    assert entry is not None and entry.app.value == "folio"


async def test_rejection_comment_reaches_the_agent(
    client: AsyncClient, team: Team, space: str
) -> None:
    submission = await agent_submits(client, team, space, "Borrador malo")
    i, a = team.instance.headers, team.agent.headers
    r = await client.post(f"{API}/submissions/{submission['id']}/reject", headers=i, json={})
    assert r.status_code == 422 and "agent reads" in r.json()["detail"]
    r = await client.post(
        f"{API}/submissions/{submission['id']}/reject",
        headers=i,
        json={"comment": "Falta el diagrama."},
    )
    assert r.json()["status"] == "rejected"
    mine = (await client.get(f"{API}/submissions", params={"status": "rejected"}, headers=a)).json()
    assert mine["items"][0]["review_comment"] == "Falta el diagrama."
    r = await client.post(f"{API}/submissions/{submission['id']}/approve", headers=i, json={})
    assert r.status_code == 409


async def test_only_reviewers_see_and_decide(client: AsyncClient, team: Team, space: str) -> None:
    submission = await agent_submits(client, team, space, "Privado")
    luis = team.member.headers
    assert (await client.get(f"{API}/submissions", headers=luis)).json()["items"] == []
    assert (
        await client.get(f"{API}/submissions/{submission['id']}", headers=luis)
    ).status_code == 404
    r = await client.post(f"{API}/submissions/{submission['id']}/approve", headers=luis, json={})
    assert r.status_code == 404
    r = await client.get(
        f"{API}/submissions/00000000-0000-0000-0000-000000000000", headers=team.instance.headers
    )
    assert r.status_code == 404 and "lists yours" in r.json()["detail"]
