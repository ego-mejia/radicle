"""Admins choose which MCP tools an agent may call; the rest are hidden and refused."""

from httpx import AsyncClient

from radicle.docket.core import mcp_catalog
from radicle.folio.mcp import catalog as folio_catalog
from tests.conftest import Team
from tests.mcp.conftest import McpFor, error_text, folio_mcp, payload

API = "/api/v1"
READER = ["whoami", "search_tickets", "get_ticket"]


async def test_catalog_lists_every_registered_tool(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    r = await client.get(f"{API}/mcp/tools", headers=board.instance.headers)
    assert r.status_code == 200, r.text
    catalog = r.json()
    async with mcp_for(board.agent) as mcp:
        registered = {t.name for t in (await mcp.list_tools()).tools}
    async with folio_mcp(client, board.agent) as folio:
        on_folio = {t.name for t in (await folio.list_tools()).tools}
    assert [t["name"] for t in catalog] == [*mcp_catalog.TOOLS, *folio_catalog.READ]
    assert set(mcp_catalog.TOOLS) == registered
    assert {t.name for t in folio_catalog.CATALOG} == on_folio
    assert next(t for t in catalog if t["name"] == "get_page")["group"] == "folio_read"
    whoami = next(t for t in catalog if t["name"] == "whoami")
    assert whoami["group"] == "context" and whoami["read_only"] and whoami["description"]
    assert not next(t for t in catalog if t["name"] == "create_ticket")["read_only"]
    # Only instance admins manage agents.
    r = await client.get(f"{API}/mcp/tools", headers=board.admin.headers)
    assert r.status_code == 403


async def test_a_limited_agent_sees_and_calls_only_its_tools(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    r = await client.patch(
        f"{API}/users/{board.agent.handle}",
        headers=board.instance.headers,
        json={"mcp_tools": [*READER, "whoami"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["mcp_tools"] == ["whoami", "search_tickets", "get_ticket"]
    async with mcp_for(board.agent) as mcp:
        names = {t.name for t in (await mcp.list_tools()).tools}
        assert names == set(READER)
        assert payload(await mcp.call_tool("whoami", {}))["handle"] == board.agent.handle
        refused = await mcp.call_tool(
            "create_ticket", {"project": "PA", "type": "task", "title": "Nope", "area": "Backend"}
        )
        assert "'create_ticket' tool is turned off" in error_text(refused)

    # Back to every tool.
    r = await client.patch(
        f"{API}/users/{board.agent.handle}",
        headers=board.instance.headers,
        json={"mcp_tools": None},
    )
    assert r.json()["mcp_tools"] is None
    async with mcp_for(board.agent) as mcp:
        assert len((await mcp.list_tools()).tools) == len(mcp_catalog.TOOLS)

    entries = (
        await client.get(f"{API}/audit", headers=board.instance.headers, params={"action": "agent"})
    ).json()["items"]
    limited = next(e for e in entries if e["details"]["after"]["mcp_tools"] == READER)
    assert limited["details"]["before"]["mcp_tools"] is None


async def test_create_with_limits_and_validation(client: AsyncClient, board: Team) -> None:
    r = await client.post(
        f"{API}/agents",
        headers=board.instance.headers,
        json={"handle": "reader-bot", "display_name": "Reader", "mcp_tools": ["get_ticket"]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["agent"]["mcp_tools"] == ["get_ticket"]

    r = await client.post(
        f"{API}/agents",
        headers=board.instance.headers,
        json={"handle": "bad-bot", "display_name": "Bad", "mcp_tools": ["drop_database"]},
    )
    assert r.status_code == 422
    assert "Unknown MCP tool: drop_database" in r.json()["detail"]

    # People follow their project permissions, not tool limits.
    r = await client.patch(
        f"{API}/users/{board.member.handle}",
        headers=board.instance.headers,
        json={"mcp_tools": ["whoami"]},
    )
    assert r.status_code == 422 and r.json()["type"].endswith("/not_an_agent")

    # Only instance admins.
    r = await client.patch(
        f"{API}/users/reader-bot", headers=board.admin.headers, json={"mcp_tools": None}
    )
    assert r.status_code == 403
