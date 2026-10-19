import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

import httpx2
import pytest
from httpx import AsyncClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from radicle.mcp.server import server
from tests.conftest import Actor

McpFor = Callable[[Actor], AbstractAsyncContextManager[Client]]


@pytest.fixture
async def mcp_for(client: AsyncClient) -> AsyncIterator[McpFor]:
    """Connect an MCP client over Streamable HTTP to the same in-memory app and DB."""
    app = client._transport.app  # type: ignore[attr-defined]

    @asynccontextmanager
    async def connect(actor: Actor) -> AsyncIterator[Client]:
        http = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), headers=actor.headers, timeout=30
        )
        async with http, Client(streamable_http_client("http://test/mcp", http_client=http)) as c:
            yield c

    # The session manager must start and stop in the same task, so it gets its own.
    started, stop = asyncio.Event(), asyncio.Event()

    async def run_manager() -> None:
        async with server.session_manager.run():
            started.set()
            await stop.wait()

    task = asyncio.create_task(run_manager())
    await started.wait()
    try:
        yield connect
    finally:
        stop.set()
        await task


def payload(result: Any) -> Any:
    """Structured result of a successful tool call."""
    assert not result.is_error, result.content[0].text
    data = result.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


def error_text(result: Any) -> str:
    assert result.is_error, "expected a tool error"
    return str(result.content[0].text)
