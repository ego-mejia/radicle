"""Folio's MCP server at /mcp/folio (Folio 0.5). Same tokens as /mcp; each tool calls the
REST API in process, so it follows Folio's roles exactly like the web app."""

from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import Context

from radicle import __version__
from radicle.platform.mcp import http
from radicle.platform.mcp.api import api
from radicle.platform.mcp.server import LimitedMCPServer

INSTRUCTIONS = """Radicle Folio is the documentation suite of Radicle. Call whoami first to
learn your handle and your global Folio role (reader, creator or admin)."""

server = LimitedMCPServer(
    name="radicle-folio", title="Radicle Folio", version=__version__, instructions=INSTRUCTIONS
)


@server.tool()
async def whoami(ctx: Context) -> dict[str, Any]:
    """Who you are connected as (user or agent) and your global Folio role."""
    async with api(ctx) as client:
        me = await client.call("GET", "/folio/me")
    return {k: me[k] for k in ("handle", "display_name", "kind", "role")}


def mount(app: FastAPI) -> None:
    """Add /mcp/folio, behind the same token check as /mcp."""
    http.mount(app, server, "/mcp/folio")
