"""Folio's comment tools (Folio 2.3): an agent reads the discussion, comments on a phrase,
replies and resolves."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish
from tests.mcp.conftest import error_text, folio_mcp, payload

MD = "# Agentes\n\nCrea el agente en Admin y conéctalo por MCP con su token.\n"


async def _page(client: AsyncClient, team: Team) -> str:
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


async def test_an_agent_comments_replies_and_resolves(client: AsyncClient, team: Team) -> None:
    page = await _page(client, team)
    async with folio_mcp(client, team.agent) as folio:
        args = {"id": page, "body": "Falta el ejemplo.", "quote": "por MCP"}
        inline = payload(await folio.call_tool("add_comment", args))
        assert inline["kind"] == "inline" and inline["quote"] == "por MCP"
        footer = payload(await folio.call_tool("add_comment", {"id": page, "body": "Revisado."}))
        args = {"id": page, "body": "Agregado.", "thread_id": inline["thread_id"]}
        reply = payload(await folio.call_tool("add_comment", args))
        assert [c["body"] for c in reply["comments"]] == ["Falta el ejemplo.", "Agregado."]
        threads = payload(await folio.call_tool("list_comments", {"id": page}))
        assert {t["thread_id"] for t in threads} == {inline["thread_id"], footer["thread_id"]}
        args = {"thread_id": inline["thread_id"]}
        assert payload(await folio.call_tool("resolve_comment", args))["resolved"]
        assert len(payload(await folio.call_tool("list_comments", {"id": page}))) == 1
        args = {"id": page, "include_resolved": True}
        assert len(payload(await folio.call_tool("list_comments", args))) == 2


async def test_errors_say_what_to_fix(client: AsyncClient, team: Team) -> None:
    page = await _page(client, team)
    async with folio_mcp(client, team.agent) as folio:
        args = {"id": page, "body": "x", "quote": "no aparece"}
        assert "Quote it exactly" in error_text(await folio.call_tool("add_comment", args))
        text = error_text(await folio.call_tool("add_comment", {"id": page, "body": " "}))
        assert "Write something" in text
        missing = "00000000-0000-0000-0000-000000000000"
        text = error_text(await folio.call_tool("resolve_comment", {"thread_id": missing}))
        assert "not found" in text.lower()
