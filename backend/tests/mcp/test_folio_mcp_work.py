"""Folio's tools for an agent's day (Folio 2.4): tasks, watch, feed and notifications,
each with a success and an error case; restricted pages stay out."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import quality
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish
from tests.mcp.conftest import error_text, folio_mcp, payload


async def _page(client: AsyncClient, team: Team, title: str) -> str:
    r = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": "docs", "kind": "page", "title": title},
    )
    await publish(client, team, r.json()["id"])
    return str(r.json()["id"])


async def test_an_agent_works_its_tasks_and_follows(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    minuta = await _page(client, team, "Minuta")
    other = await _page(client, team, "Guía")
    md = f"::task[Resumir el repo]{{id=ai-1 assignee={team.agent.handle} due={quality.today()}}}"
    await client.put(f"{API}/nodes/{minuta}/draft", headers=i, json={"content_md": md})
    await run_jobs(db)
    async with folio_mcp(client, team.agent) as folio:
        tasks = payload(await folio.call_tool("list_my_tasks"))
        assert [(t["text"], t["bucket"], t["page"]["title"]) for t in tasks] == [
            ("Resumir el repo", "today", "Minuta")
        ]
        notes = payload(await folio.call_tool("list_notifications", {"mark_read": True}))
        assert notes["unread"] == 1 and "assigned you a task" in notes["items"][0]["title"]
        assert payload(await folio.call_tool("list_notifications"))["items"] == []

        done = payload(await folio.call_tool("set_task_done", {"id": tasks[0]["id"]}))
        assert done["done"] is True
        assert payload(await folio.call_tool("list_my_tasks")) == []

        followed = payload(await folio.call_tool("watch", {"target_type": "space", "id": "docs"}))
        assert followed["following"] is True
        payload(await folio.call_tool("watch", {"target_type": "node", "id": other}))
        feed = payload(await folio.call_tool("get_feed"))
        assert {f["title"] for f in feed} == {"Minuta", "Guía"}
        assert {f["reason"] for f in feed} == {"following"}
        unfollowed = payload(
            await folio.call_tool("watch", {"target_type": "space", "id": "docs", "follow": False})
        )
        assert unfollowed["following"] is False


async def test_errors_and_restricted_pages(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    secret = await _page(client, team, "Secreto")
    md = f"::task[Algo]{{id=ai-1 assignee={team.agent.handle}}}"
    await client.put(f"{API}/nodes/{secret}/draft", headers=i, json={"content_md": md})
    await client.put(
        f"{API}/nodes/{secret}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    async with folio_mcp(client, team.agent) as folio:
        assert payload(await folio.call_tool("list_my_tasks", {"status": "all"})) == []
        assert payload(await folio.call_tool("get_feed")) == []
        text = error_text(await folio.call_tool("watch", {"target_type": "node", "id": secret}))
        assert "not found" in text.lower()
        text = error_text(await folio.call_tool("watch", {"target_type": "space", "id": "nada"}))
        assert "not found" in text.lower()
        bad = "00000000-0000-0000-0000-000000000000"
        assert (
            "not found" in error_text(await folio.call_tool("set_task_done", {"id": bad})).lower()
        )
        text = error_text(await folio.call_tool("list_my_tasks", {"status": "nope"}))
        assert "status" in text.lower()
