"""Serving an app's MCP server over Streamable HTTP, behind the same token check."""

import json
from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from radicle.platform.mcp.api import APIError, RadicleAPI, attach


class RequireToken:
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


def mount(
    app: FastAPI, server: MCPServer, path: str, *, max_request_body_size: int = 1024 * 1024
) -> None:
    """Add POST/GET/DELETE `path` to the app, every request through RequireToken. The
    server's session manager runs in the app lifespan."""
    attach(app)
    starlette_app = server.streamable_http_app(
        streamable_http_path=path,
        stateless_http=True,
        json_response=True,
        # Auth is a bearer header, never a cookie, so DNS rebinding cannot borrow it.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        host="0.0.0.0",  # noqa: S104 - only disables the localhost-only default
        max_request_body_size=max_request_body_size,
    )
    route = starlette_app.routes[0]
    if not isinstance(route, Route):  # pragma: no cover - SDK layout changed
        raise RuntimeError("Unexpected MCP app layout")
    app.router.routes.insert(
        0, Route(path, endpoint=RequireToken(route.endpoint), methods=["GET", "POST", "DELETE"])
    )
