"""Live notification signals for the SSE stream (ADR 0038). One LISTEN connection per
process receives `NOTIFY radicle_notifications '<user id>'` and wakes that user's streams,
so any number of open tabs costs one database connection."""

import asyncio
import contextlib
import logging
from typing import Any

import asyncpg

from radicle.platform.config import get_settings
from radicle.platform.services.events import CHANNEL

log = logging.getLogger("radicle.notify")


def _dsn(database_url: str) -> str:
    scheme, _, rest = database_url.partition("://")
    return f"{scheme.split('+')[0]}://{rest}"


class Hub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = {}
        self._connection: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_listening(self) -> None:
        async with self._lock:
            if self._connection is not None and not self._connection.is_closed():
                return
            self._connection = await asyncpg.connect(_dsn(get_settings().database_url))
            await self._connection.add_listener(CHANNEL, self._on_notify)

    def _on_notify(self, _conn: Any, _pid: int, _channel: str, payload: str) -> None:
        self.publish(payload)

    def publish(self, user_id: str) -> None:
        for queue in self._subscribers.get(user_id, set()):
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(user_id)

    @contextlib.asynccontextmanager
    async def subscribe(self, user_id: str, *, listen: bool = True) -> Any:
        """A queue that receives a signal each time the user gets a notification."""
        if listen:
            await self._ensure_listening()
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=16)
        self._subscribers.setdefault(user_id, set()).add(queue)
        try:
            yield queue
        finally:
            self._subscribers[user_id].discard(queue)
            if not self._subscribers[user_id]:
                del self._subscribers[user_id]

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed():
            await self._connection.close()
        self._connection = None


hub = Hub()
