"""MCP server over Streamable HTTP at /mcp, mounted in the Radicle app."""

import json
from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ListToolsResult

from radicle import __version__
from radicle.docket.mcp import tools
from radicle.docket.mcp.guide import rql_guide
from radicle.platform.mcp import http
from radicle.platform.mcp.api import api

INSTRUCTIONS = """Radicle is a ticket tracker. You work tickets like a teammate.
Typical flow: whoami, then my_tickets or search_tickets, get_ticket for details, then
transition_ticket, set_checklist_item, update_ticket and add_comment as you work.
Tickets are referred to by key (PA-4), people by handle, areas and milestones by name.
Read radicle://guide/rql for the query language. Errors explain what is valid instead."""


class RadicleMCPServer(MCPServer):
    """Agents limited to some tools (Admin → Users) only see and call those."""

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


server: MCPServer = RadicleMCPServer(
    name="radicle", title="Radicle", version=__version__, instructions=INSTRUCTIONS
)
tools.register(server)


@server.resource(
    "radicle://guide/rql",
    name="rql-guide",
    title="RQL guide",
    description="Fields, operators and examples of the Radicle Query Language",
    mime_type="text/markdown",
)
def guide() -> str:
    return rql_guide()


@server.resource(
    "radicle://projects/{key}/schema",
    name="project-schema",
    title="Project schema",
    description="Areas, open milestones, workflows and members of a project",
    mime_type="application/json",
)
async def project_schema(key: str, ctx: Context) -> str:
    async with api(ctx) as client:
        project = await client.call("GET", f"/projects/{key}")
    return json.dumps(tools.project_schema(project), ensure_ascii=False, indent=2)


def mount(app: FastAPI) -> None:
    """Add POST/GET/DELETE /mcp to the app, behind platform's token check. The session
    manager runs in the app lifespan."""
    # upload_attachment takes up to 10 MB, about 13.4 MB once in base64.
    http.mount(app, server, "/mcp", max_request_body_size=16 * 1024 * 1024)
