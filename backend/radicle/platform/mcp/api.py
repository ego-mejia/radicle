"""In-process calls from MCP tools to the REST API, forwarding the caller's token.

Going through REST keeps one source of truth: the MCP gets exactly the same
validation, permissions and history as the API.
"""

import json as json_lib
from typing import Any

import httpx
from fastapi import FastAPI
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

_app: FastAPI | None = None


def attach(app: FastAPI) -> None:
    global _app
    _app = app


class RadicleAPI:
    def __init__(self, token: str) -> None:
        if _app is None:  # pragma: no cover - attach() runs at startup
            raise RuntimeError("MCP is not attached to the Radicle app")
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://radicle.internal/api/v1",
            headers={"Authorization": f"Bearer {token}"},
        )

    async def __aenter__(self) -> "RadicleAPI":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def call(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.request(
            method,
            path,
            json=json,
            params={k: v for k, v in (params or {}).items() if v is not None},
            headers=headers,
            files=files,
            data={k: v for k, v in (data or {}).items() if v is not None} or None,
        )
        if response.status_code >= 400:
            raise APIError(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def events(self, path: str, json: Any) -> list[tuple[str, Any]]:
        """POST to a server-sent events route and read every event once it ends."""
        response = await self._client.post(path, json=json)
        if response.status_code >= 400:
            raise APIError(response)
        out: list[tuple[str, Any]] = []
        for block in response.text.strip().split("\n\n"):
            fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
            if "event" in fields:
                out.append((fields["event"], json_lib.loads(fields.get("data", "null"))))
        return out

    async def raw(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        response = await self._client.get(path, params=params)
        if response.status_code >= 400:
            raise APIError(response)
        return response


class APIError(ToolError):
    """A REST problem turned into an actionable tool error."""

    def __init__(self, response: httpx.Response) -> None:
        try:
            problem = response.json()
        except ValueError:
            problem = {}
        self.status = response.status_code
        self.problem = problem if isinstance(problem, dict) else {}
        detail = self.problem.get("detail") or response.reason_phrase or "Request failed"
        super().__init__(str(detail))


def token_from(ctx: Context) -> str:
    headers = ctx.headers or {}
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ToolError("Missing token. Connect with 'Authorization: Bearer rdc_...'.")
    return token.strip()


def api(ctx: Context) -> RadicleAPI:
    return RadicleAPI(token_from(ctx))
