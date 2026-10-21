"""Folio analytics over MCP (5.9): a page's readership, and what people search for or ask
without an answer, so an agent can propose what to document next."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from pydantic import Field

from radicle.platform.mcp.api import api

Days = Annotated[int, Field(ge=1, le=365, description="How many days back")]


def register(server: MCPServer) -> None:
    @server.tool()
    async def get_page_analytics(
        ctx: Context,
        id: Annotated[str, Field(description="The page id")],
        days: Days = 30,
    ) -> dict[str, Any]:
        """Views and unique readers per day, total views, approximate reading time, and who
        read it when the space allows naming readers. For the page owner and space admins."""
        async with api(ctx) as client:
            data: dict[str, Any] = await client.call(
                "GET", f"/folio/analytics/pages/{id}", params={"days": days}
            )
        return data

    @server.tool()
    async def get_search_gaps(ctx: Context, days: Days = 30) -> dict[str, Any]:
        """What people searched in Folio without a result (most frequent first) and the chat
        questions the docs didn't answer. Use it to propose what to document. Folio admins."""
        async with api(ctx) as client:
            site = await client.call("GET", "/folio/analytics/site", params={"days": days})
        return {"no_results": site["no_results"], "unanswered": site["unanswered"]}
