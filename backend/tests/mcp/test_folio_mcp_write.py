"""Folio's MCP write tools (Folio 1.7). Acceptance: an agent connected over MCP writes a
post from a repo and it waits for an admin's approval; the outcome reaches the agent."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, METADATA, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload

README = """Radicle is a self-hosted ticket tracker with MCP.

# Quick start

Run `docker compose up -d` and open http://localhost:8000.

# Connect an agent

Create the agent in Admin and connect it with its token.
"""


async def _space(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, team, "eng")


async def test_acceptance_an_agent_posts_from_a_repo(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await _space(client, team)
    async with folio_mcp(client, team.agent) as folio:
        assert payload(await folio.call_tool("search_docs", {"query": "quick start"})) == []
        schema = payload(await folio.call_tool("get_metadata_schema"))
        assert schema["doc_types"]
        args = {
            "space": "eng",
            "kind": "blog_post",
            "title": "Radicle en 5 minutos",
            "content_md": README,
            "metadata": METADATA,
        }
        made = payload(await folio.call_tool("create_page", args))
        assert made["saved"] and made["space"] == "eng"
        sent = payload(
            await folio.call_tool(
                "submit_for_publication", {"id": made["id"], "change_note": "Desde el README"}
            )
        )
        assert sent["status"] == "pending"
        mine = payload(await folio.call_tool("list_my_submissions", {"status": "pending"}))
        assert [s["title"] for s in mine] == ["Radicle en 5 minutos"]

        # A Folio admin approves it from the queue (REST, as the web app does).
        i = team.instance.headers
        url = f"{API}/submissions/{sent['submission_id']}/approve"
        r = await client.post(url, headers=i, json={})
        assert r.status_code == 201, r.text
        await run_jobs(db)
        done = payload(await folio.call_tool("list_my_submissions"))
        assert done[0]["status"] == "approved" and done[0]["version"] == 1
        page = payload(await folio.call_tool("get_page", {"id": made["id"]}))
        assert page["version"] == 1 and "# Connect an agent" in page["content_md"]
        hits = payload(await folio.call_tool("search_docs", {"query": "connect an agent"}))
        assert hits[0]["node_id"] == made["id"] and hits[0]["section"] == ["Connect an agent"]


async def test_rejections_and_fixes(client: AsyncClient, team: Team) -> None:
    await _space(client, team)
    async with folio_mcp(client, team.agent) as folio:
        args = {"space": "eng", "title": "Guía", "content_md": "Hola", "metadata": {}}
        made = payload(await folio.call_tool("create_page", args))
        text = error_text(
            await folio.call_tool("submit_for_publication", {"id": made["id"], "change_note": "x"})
        )
        assert "description" in text and "doc_type" in text and "owner" in text
        assert "Send content_md" in error_text(
            await folio.call_tool("update_draft", {"id": made["id"]})
        )
        fixed = payload(
            await folio.call_tool("update_draft", {"id": made["id"], "metadata": METADATA})
        )
        assert fixed["metadata"]["doc_type"] == "how-to"
        sent = payload(
            await folio.call_tool("submit_for_publication", {"id": made["id"], "change_note": "x"})
        )
        r = await client.post(
            f"{API}/submissions/{sent['submission_id']}/reject",
            headers=team.instance.headers,
            json={"comment": "Falta el diagrama."},
        )
        assert r.status_code == 200, r.text
        mine = payload(await folio.call_tool("list_my_submissions", {"status": "rejected"}))
        assert mine[0]["review_comment"] == "Falta el diagrama."


async def test_a_reader_agent_cannot_write(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    async with folio_mcp(client, team.agent) as folio:
        args = {"space": "eng", "title": "Guía", "content_md": "Hola", "metadata": METADATA}
        assert "creator role" in error_text(await folio.call_tool("create_page", args))


async def test_a_bad_draft_keeps_the_page_and_says_how_to_fix(
    client: AsyncClient, team: Team
) -> None:
    await _space(client, team)
    async with folio_mcp(client, team.agent) as folio:
        args = {
            "space": "eng",
            "title": "Guía",
            "content_md": "Hola",
            "metadata": {f"field_{n}": n for n in range(100)},
        }
        text = error_text(await folio.call_tool("create_page", args))
        assert "was created (id " in text and "update_draft" in text and "metadata" in text
