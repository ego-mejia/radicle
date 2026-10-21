"""/mcp/folio (Folio 0.5): the same token works on both MCP servers."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.mcp.conftest import McpFor, error_text, folio_mcp, payload


async def test_whoami_on_both_servers_with_one_token(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    async with mcp_for(board.agent) as docket:
        assert payload(await docket.call_tool("whoami"))["handle"] == "agent-backend"
    async with folio_mcp(client, board.agent) as folio:
        tools = [t.name for t in (await folio.list_tools()).tools]
        assert tools[0] == "whoami" and "search_docs" in tools
        me = payload(await folio.call_tool("whoami"))
        assert me == {
            "handle": "agent-backend",
            "display_name": me["display_name"],
            "kind": "agent",
            "role": "reader",
            "spaces": [],
        }


async def test_whoami_explains_missing_access(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    grants = (await client.get("/api/v1/folio/admin/grants", headers=i)).json()["items"]
    await client.delete(f"/api/v1/folio/admin/grants/{grants[0]['id']}", headers=i)
    async with folio_mcp(client, board.agent) as folio:
        assert "no access to Folio" in error_text(await folio.call_tool("whoami"))


async def test_folio_mcp_rejects_missing_tokens(client: AsyncClient, board: Team) -> None:
    r = await client.post("/mcp/folio", json={})
    assert r.status_code == 401 and "Bearer" in r.json()["detail"]


async def test_tool_limits_apply_on_folio_too(client: AsyncClient, board: Team) -> None:
    r = await client.patch(
        f"/api/v1/users/{board.agent.handle}",
        headers=board.instance.headers,
        json={"mcp_tools": ["get_ticket"]},
    )
    assert r.status_code == 200, r.text
    async with folio_mcp(client, board.agent) as folio:
        assert (await folio.list_tools()).tools == []
        assert "turned off for this agent" in error_text(await folio.call_tool("whoami"))
