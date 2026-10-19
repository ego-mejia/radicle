"""MCP server over Streamable HTTP at /mcp, mounted in the Radicle app."""

import json
from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from radicle import __version__
from radicle.mcp import tools
from radicle.mcp.api import APIError, RadicleAPI, api, attach
from radicle.mcp.guide import rql_guide

INSTRUCTIONS = """Radicle is a ticket tracker. You work tickets like a teammate.
Typical flow: whoami, then my_tickets or search_tickets, get_ticket for details, then
transition_ticket, set_checklist_item, update_ticket and add_comment as you work.
Tickets are referred to by key (PA-4), people by handle, areas and milestones by name.
Read radicle://guide/rql for the query language. Errors explain what is valid instead."""

server: MCPServer = MCPServer(
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


class _RequireToken:
    """Reject connections without a valid, unrevoked token before MCP sees them."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = dict(scope.get("headers") or [])
        authorization = headers.get(b"authorization", b"").decode()
        scheme, _, token = authorization.partition(" ")
        detail = None
        if scheme.lower() != "bearer" or not token.strip():
            detail = "Connect with 'Authorization: Bearer rdc_...' (an agent or personal token)."
        else:
            async with RadicleAPI(token.strip()) as client:
                try:
                    await client.call("GET", "/me")
                except APIError as exc:
                    detail = str(exc)
        if detail is not None:
            body = json.dumps({"error": "unauthorized", "detail": detail}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b'Bearer realm="radicle"'),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def mount(app: FastAPI) -> None:
    """Add POST/GET/DELETE /mcp to the app. The session manager runs in the app lifespan."""
    attach(app)
    starlette_app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        # Auth is a bearer header, never a cookie, so DNS rebinding cannot borrow it.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        host="0.0.0.0",  # noqa: S104 - only disables the localhost-only default
        # upload_attachment takes up to 10 MB, about 13.4 MB once in base64.
        max_request_body_size=16 * 1024 * 1024,
    )
    route = starlette_app.routes[0]
    if not isinstance(route, Route):  # pragma: no cover - SDK layout changed
        raise RuntimeError("Unexpected MCP app layout")
    endpoint = route.endpoint
    app.router.routes.insert(
        0, Route("/mcp", endpoint=_RequireToken(endpoint), methods=["GET", "POST", "DELETE"])
    )
