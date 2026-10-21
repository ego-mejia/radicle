"""An MCP server that honors agents' tool limits (Admin → Users → MCP permissions)."""

from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ListToolsResult

from radicle.platform.mcp.api import api


class LimitedMCPServer(MCPServer):
    """Agents limited to some tools only see and call those, on every server."""

    async def _handle_list_tools(self, ctx: Any, params: Any) -> ListToolsResult:
        tools = await self.list_tools()
        allowed = await _allowed_tools(Context(request_context=ctx, mcp_server=self))
        if allowed is not None:
            tools = [t for t in tools if t.name in allowed]
        return ListToolsResult(tools=tools)

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context | None = None
    ) -> Any:
        if context is not None and context.request_context is not None:
            allowed = await _allowed_tools(context)
            if allowed is not None and name not in allowed:
                raise ToolError(
                    f"The '{name}' tool is turned off for this agent. An instance admin can "
                    "turn it on in Admin → Users → MCP permissions."
                )
        return await super().call_tool(name, arguments, context)


async def _allowed_tools(ctx: Context) -> set[str] | None:
    """The caller's MCP tool limit, or None when it may use them all."""
    async with api(ctx) as client:
        me = await client.call("GET", "/me")
    tools = me.get("mcp_tools")
    return None if tools is None else set(tools)
