"""A Yjs client over an in-process ASGI WebSocket, for Folio's real-time tests.

It runs in the test's event loop, so the room shares the test's database session, and
speaks the same protocol as `y-websocket` in the browser.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Any

import pycrdt
from httpx import AsyncClient

from radicle.folio.services import ydoc


class Rejected(Exception):
    def __init__(self, code: int, reason: str) -> None:
        super().__init__(f"{code} {reason}")
        self.code = code
        self.reason = reason


class YClient:
    def __init__(self, app: Any, path: str, headers: dict[str, str]) -> None:
        self.app = app
        self.path, _, query = path.partition("?")
        self.query = query
        self.headers = headers
        self.doc: pycrdt.Doc[Any] = pycrdt.Doc()
        self.awareness: dict[int, Any] = {}
        self.peer_awareness = pycrdt.Awareness(pycrdt.Doc())
        self.mine = pycrdt.Awareness(self.doc)
        self._inbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._outbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._reader: asyncio.Task[None] | None = None
        self._sending = False
        self.doc.observe(self._on_change)

    def _on_change(self, event: Any) -> None:
        if not self._sending:
            update = pycrdt.create_update_message(event.update)
            self._inbox.put_nowait({"type": "websocket.receive", "bytes": update})

    async def connect(self) -> None:
        scope = {
            "type": "websocket",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": self.query.encode(),
            "headers": [(k.lower().encode(), v.encode()) for k, v in self.headers.items()],
            "scheme": "ws",
            "server": ("test", 80),
            "client": ("10.0.0.1", 1234),
            "subprotocols": [],
            "root_path": "",
        }
        await self._inbox.put({"type": "websocket.connect"})
        self._task = asyncio.create_task(self.app(scope, self._inbox.get, self._outbox.put))
        first = await asyncio.wait_for(self._outbox.get(), 5)
        if first["type"] == "websocket.close":
            raise Rejected(first.get("code", 1000), first.get("reason", ""))
        assert first["type"] == "websocket.accept", first
        self._reader = asyncio.create_task(self._read())
        await self.send(pycrdt.create_sync_message(self.doc))

    async def _read(self) -> None:
        while True:
            message = await self._outbox.get()
            if message["type"] != "websocket.send":
                return
            data: bytes = message["bytes"]
            if data[0] == pycrdt.YMessageType.SYNC:
                self._sending = True
                try:
                    reply = pycrdt.handle_sync_message(data[1:], self.doc)
                finally:
                    self._sending = False
                if reply is not None:
                    await self.send(reply)
            elif data[0] == pycrdt.YMessageType.AWARENESS:
                self.peer_awareness.apply_awareness_update(pycrdt.read_message(data[1:]), None)

    async def send(self, data: bytes) -> None:
        await self._inbox.put({"type": "websocket.receive", "bytes": data})

    async def set_awareness(self, state: dict[str, Any]) -> None:
        self.mine.set_local_state(state)
        update = self.mine.encode_awareness_update([self.doc.client_id])
        await self.send(pycrdt.create_awareness_message(update))

    def json(self) -> dict[str, Any]:
        return ydoc.to_json(self.doc)

    async def close(self) -> None:
        await self._inbox.put({"type": "websocket.disconnect", "code": 1000})
        if self._task is not None:
            await asyncio.wait_for(self._task, 5)
        if self._reader is not None:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader


@contextlib.asynccontextmanager
async def connected(
    client: AsyncClient, node_id: str, headers: dict[str, str]
) -> AsyncIterator[YClient]:
    app = client._transport.app  # type: ignore[attr-defined]
    headers = dict(headers)
    if any(k.lower() == "x-csrf-token" for k in headers) and client.cookies:
        # The instance admin signs in with the shared client's session cookie.
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
    y = YClient(app, f"/api/v1/folio/collab/{node_id}", headers)
    await y.connect()
    try:
        yield y
    finally:
        await y.close()


async def settle(predicate: Any, within: float = 3.0) -> None:
    """Let the messages flow until the predicate holds."""
    deadline = asyncio.get_running_loop().time() + within
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("the clients did not converge")
        await asyncio.sleep(0.01)
