"""Folio's MCP server at /mcp/folio (Folio 0.5). Same tokens as /mcp; each tool calls the
REST API in process, so it follows Folio's roles exactly like the web app."""

from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import Context

from radicle import __version__
from radicle.folio.mcp import comments, read, templates, work, write
from radicle.platform.mcp import http
from radicle.platform.mcp.api import api
from radicle.platform.mcp.server import LimitedMCPServer

INSTRUCTIONS = """Radicle Folio is the documentation suite of Radicle. Call whoami first to
learn your handle, your global Folio role (reader, creator or admin) and your spaces.
To find docs use search_docs (words or a question) or query_docs (RQL), then get_page for
the Markdown. Before writing, search whether the doc already exists and read
get_metadata_schema; then create_page or update_draft in Markdown, submit_for_publication
(agents wait for a Folio admin's approval) and check list_my_submissions for the outcome.
Errors explain what is valid instead."""

server = LimitedMCPServer(
    name="radicle-folio", title="Radicle Folio", version=__version__, instructions=INSTRUCTIONS
)


@server.tool()
async def whoami(ctx: Context) -> dict[str, Any]:
    """Who you are connected as (user or agent), your global Folio role and the spaces
    you can see with what you may do in each."""
    async with api(ctx) as client:
        me = await client.call("GET", "/folio/me")
        spaces = await client.call("GET", "/folio/spaces")
    listed = [{"key": s["key"], "permissions": s["permissions"]} for s in spaces["items"]]
    return {k: me[k] for k in ("handle", "display_name", "kind", "role")} | {"spaces": listed}


read.register(server)
write.register(server)
templates.register(server)
comments.register(server)
work.register(server)


def mount(app: FastAPI) -> None:
    """Add /mcp/folio, behind the same token check as /mcp."""
    http.mount(app, server, "/mcp/folio")
