"""Real-time rooms (Folio 2.2, ADR 0039): one per open document, in this process.

A room holds the node's Y.Doc and its peers. It speaks the Yjs protocol (sync and
awareness messages, as `y-websocket` does in the browser): each update a peer sends is
applied, stored in folio_yupdates and sent to the others. Every few seconds the draft's
JSON follows the Y.Doc, every 30 s the updates are compacted, and when the last peer
leaves both happen and the room closes.

Changes made outside the room (an agent over REST or MCP) go through `apply_change`, so
whoever is editing sees them arrive, labelled with the agent's name.
"""

import asyncio
import contextlib
import logging
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any

import pycrdt
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import ystore
from radicle.platform.db.models import User, UserKind
from radicle.platform.db.session import get_sessionmaker
from radicle.platform.errors import ProblemError

log = logging.getLogger("radicle.folio.collab")

MAX_PEERS = 50
SAVE_EVERY = 5.0  # seconds between draft JSON refreshes
COMPACT_EVERY = 30.0
AWARENESS_PER_SECOND = 30
AGENT_LABEL_SECONDS = 10.0
# Readable on light and dark backgrounds alike.
COLORS = ("#2563EB", "#DB2777", "#D97706", "#059669", "#7C3AED", "#DC2626", "#0891B2", "#65A30D")

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class RoomFull(ProblemError):
    status = 429
    code = "room_full"


@contextlib.asynccontextmanager
async def _committed_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as db:
        yield db
        await db.commit()


# Rooms outlive any request, so they open their own sessions. Tests swap this.
sessions: SessionFactory = _committed_session


def color_for(user_id: uuid.UUID) -> str:
    return COLORS[user_id.int % len(COLORS)]


@dataclass(eq=False)
class Peer:
    """One connection: how to send it bytes and who it is."""

    send: Callable[[bytes], Awaitable[None]]
    user: User
    awareness_ids: set[int] = field(default_factory=set)
    _recent: deque[float] = field(default_factory=deque)

    def allow_awareness(self) -> bool:
        """At most AWARENESS_PER_SECOND pointer and selection updates a second."""
        now = time.monotonic()
        while self._recent and now - self._recent[0] >= 1.0:
            self._recent.popleft()
        if len(self._recent) >= AWARENESS_PER_SECOND:
            return False
        self._recent.append(now)
        return True


class Room:
    def __init__(self, node_id: uuid.UUID, doc: pycrdt.Doc[Any]) -> None:
        self.node_id = node_id
        self.doc = doc
        self.awareness = pycrdt.Awareness(doc)
        self.peers: list[Peer] = []
        self.authors: set[uuid.UUID] = set()  # who changed it since the last snapshot
        self.lock = asyncio.Lock()
        self._outgoing: list[bytes] = []
        self._dirty = False
        self._last_compact = time.monotonic()
        self._task: asyncio.Task[None] | None = None
        self._subscription = doc.observe(self._on_change)

    def _on_change(self, event: Any) -> None:
        self._outgoing.append(event.update)

    # --- peers -------------------------------------------------------------------------

    @property
    def full(self) -> bool:
        return len(self.peers) >= MAX_PEERS

    async def join(self, peer: Peer) -> None:
        if self.full:
            raise RoomFull(
                f"{MAX_PEERS} people are editing this page already. Try again in a moment."
            )
        self.peers.append(peer)
        await peer.send(pycrdt.create_sync_message(self.doc))
        ids = list(self.awareness.states)
        if ids:
            update = self.awareness.encode_awareness_update(ids)
            await peer.send(pycrdt.create_awareness_message(update))
        if self._task is None:
            self._task = asyncio.create_task(self._tick())

    async def leave(self, peer: Peer) -> bool:
        """Drop the peer; True when it was the last one."""
        if peer in self.peers:
            self.peers.remove(peer)
        if peer.awareness_ids:
            ids = list(peer.awareness_ids & set(self.awareness.states))
            if ids:
                self.awareness.remove_awareness_states(ids, origin=peer)
                gone = self.awareness.encode_awareness_update(ids)
                await self._broadcast(pycrdt.create_awareness_message(gone), skip=None)
        return not self.peers

    async def receive(self, peer: Peer, message: bytes) -> None:
        if not message:
            return
        kind, payload = message[0], message[1:]
        if kind == pycrdt.YMessageType.SYNC:
            async with self.lock:
                reply = pycrdt.handle_sync_message(payload, self.doc)
                if reply is not None:
                    await peer.send(reply)
                if self._outgoing:
                    self.authors.add(peer.user.id)
                await self._flush_updates(skip=peer)
        elif kind == pycrdt.YMessageType.AWARENESS:
            if not peer.allow_awareness():
                return
            before = set(self.awareness.states)
            self.awareness.apply_awareness_update(pycrdt.read_message(payload), origin=peer)
            peer.awareness_ids |= set(self.awareness.states) - before
            await self._broadcast(message, skip=peer)

    async def _broadcast(self, message: bytes, skip: Peer | None) -> None:
        for other in list(self.peers):
            if other is skip:
                continue
            try:
                await other.send(message)
            except Exception:  # a dead socket leaves on its own
                log.debug("dropping a message to a closed peer", exc_info=True)

    async def _flush_updates(self, skip: Peer | None) -> None:
        """Store and send what the last change produced."""
        updates, self._outgoing = self._outgoing, []
        if not updates:
            return
        self._dirty = True
        async with sessions() as db:
            for update in updates:
                await ystore.append_update(db, self.node_id, update)
        for update in updates:
            await self._broadcast(pycrdt.create_update_message(update), skip=skip)

    # --- server-side changes -------------------------------------------------------------

    async def change(self, actor: User, edit: Callable[[pycrdt.Doc[Any]], None]) -> None:
        async with self.lock:
            edit(self.doc)
            self.authors.add(actor.id)
            await self._flush_updates(skip=None)
        if actor.kind != UserKind.human:
            await self._label(actor)

    async def _label(self, actor: User) -> None:
        """Show the agent among the editors for a few seconds, under its own client id."""
        stand_in: pycrdt.Doc[Any] = pycrdt.Doc()
        awareness = pycrdt.Awareness(stand_in)
        state = {
            "user": {
                "name": actor.display_name,
                "handle": actor.handle,
                "color": color_for(actor.id),
                "agent": True,
            }
        }
        awareness.set_local_state(state)
        update = awareness.encode_awareness_update([stand_in.client_id])
        self.awareness.apply_awareness_update(update, origin=None)
        await self._broadcast(pycrdt.create_awareness_message(update), skip=None)

        async def clear() -> None:
            await asyncio.sleep(AGENT_LABEL_SECONDS)
            awareness.set_local_state(None)
            gone = awareness.encode_awareness_update([stand_in.client_id])
            with contextlib.suppress(Exception):
                self.awareness.apply_awareness_update(gone, origin=None)
            await self._broadcast(pycrdt.create_awareness_message(gone), skip=None)

        asyncio.get_running_loop().create_task(clear())

    # --- persistence ---------------------------------------------------------------------

    async def save(self, *, compact: bool = False) -> None:
        """Bring the draft's JSON up to date and, when asked, compact the updates."""
        async with self.lock, sessions() as db:
            node = await db.get(FolioNode, self.node_id)
            if node is None:
                return
            if self._dirty:
                await ystore.save_json(db, node, self.doc)
                self._dirty = False
            if compact:
                await ystore.compact(db, self.node_id, self.doc)
                self._last_compact = time.monotonic()

    async def _tick(self) -> None:
        try:
            while self.peers:
                await asyncio.sleep(SAVE_EVERY)
                due = time.monotonic() - self._last_compact >= COMPACT_EVERY
                await self.save(compact=due)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("room %s stopped saving", self.node_id)

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._dirty = True
        await self.save(compact=True)
        self.doc.unobserve(self._subscription)


class Rooms:
    """The open rooms of this process, by node."""

    def __init__(self) -> None:
        self._rooms: dict[uuid.UUID, Room] = {}
        self._lock = asyncio.Lock()

    def get(self, node_id: uuid.UUID) -> Room | None:
        return self._rooms.get(node_id)

    async def open(self, db: AsyncSession, node: FolioNode) -> Room:
        async with self._lock:
            room = self._rooms.get(node.id)
            if room is None:
                room = Room(node.id, await ystore.load(db, node))
                self._rooms[node.id] = room
            return room

    async def leave(self, room: Room, peer: Peer) -> None:
        if await room.leave(peer):
            async with self._lock:
                if not room.peers and self._rooms.get(room.node_id) is room:
                    del self._rooms[room.node_id]
                    await room.close()

    async def close_all(self) -> None:
        for room in list(self._rooms.values()):
            await room.close()
        self._rooms.clear()


rooms = Rooms()


async def flush(node: FolioNode) -> None:
    """Make the draft's JSON match the live document now, e.g. right before publishing."""
    room = rooms.get(node.id)
    if room is not None:
        room._dirty = True
        await room.save()


async def apply_change(
    db: AsyncSession,
    node: FolioNode,
    actor: User,
    edit: Callable[[pycrdt.Doc[Any]], None],
) -> None:
    """Change a document from outside the room: live if it is open, stored if not. The
    draft's JSON follows right away either way."""
    room = rooms.get(node.id)
    if room is not None:
        await room.change(actor, edit)
        room._dirty = True
        await room.save()
        return
    doc = await ystore.load(db, node)
    before = doc.get_state()
    edit(doc)
    await ystore.append_update(db, node.id, doc.get_update(before))
    await ystore.save_json(db, node, doc)
