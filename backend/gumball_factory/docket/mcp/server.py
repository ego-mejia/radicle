"""MCP server over Streamable HTTP at /mcp, mounted in the Gumball Factory app."""

import json

from fastapi import FastAPI
from mcp.server.mcpserver import Context, MCPServer

from gumball_factory import __version__
from gumball_factory.docket.mcp import tools
from gumball_factory.docket.mcp.guide import rql_guide
from gumball_factory.platform.mcp import http
from gumball_factory.platform.mcp.api import api
from gumball_factory.platform.mcp.server import LimitedMCPServer

INSTRUCTIONS = """Gumball Factory is a ticket tracker. You work tickets like a teammate.
Typical flow: whoami, then my_tickets or search_tickets, get_ticket for details, then
transition_ticket, set_checklist_item, update_ticket and add_comment as you work.
Tickets are referred to by key (PA-4), people by handle, areas and milestones by name.
Read gumball-factory://guide/rql for the query language. Errors explain what is valid instead."""


server: MCPServer = LimitedMCPServer(
    name="gumball-factory", title="Gumball Factory", version=__version__, instructions=INSTRUCTIONS
)
tools.register(server)


@server.resource(
    "gumball-factory://guide/rql",
    name="rql-guide",
    title="RQL guide",
    description="Fields, operators and examples of the Gumball Factory Query Language",
    mime_type="text/markdown",
)
def guide() -> str:
    return rql_guide()


@server.resource(
    "gumball-factory://projects/{key}/schema",
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
