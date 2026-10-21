"""/mcp/folio (Folio 0.5): the same token works on both MCP servers."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from httpx import AsyncClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from radicle.folio.mcp.server import server as folio_server
from tests.conftest import Actor, Team
from tests.mcp.conftest import McpFor, error_text, payload


@asynccontextmanager
async def folio_mcp(client: AsyncClient, actor: Actor) -> AsyncIterator[Client]:
    app = client._transport.app  # type: ignore[attr-defined]
    started, stop = asyncio.Event(), asyncio.Event()

    async def run_manager() -> None:
        async with folio_server.session_manager.run():
            started.set()
            await stop.wait()

    task = asyncio.create_task(run_manager())
    await started.wait()
    http = httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), headers=actor.headers, timeout=30
    )
    try:
        async with (
            http,
            Client(streamable_http_client("http://test/mcp/folio", http_client=http)) as c,
        ):
            yield c
    finally:
        stop.set()
        await task


async def test_whoami_on_both_servers_with_one_token(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    async with mcp_for(board.agent) as docket:
        assert payload(await docket.call_tool("whoami"))["handle"] == "agent-backend"
    async with folio_mcp(client, board.agent) as folio:
        tools = (await folio.list_tools()).tools
        assert [t.name for t in tools] == ["whoami"]
        me = payload(await folio.call_tool("whoami"))
        assert me == {
            "handle": "agent-backend",
            "display_name": me["display_name"],
            "kind": "agent",
            "role": "reader",
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
