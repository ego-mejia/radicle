"""Real-time rooms without the socket (Folio 2.2): peers converge through the room, it
stores and compacts updates, outside changes arrive live, awareness is throttled."""

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pycrdt
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioYUpdate
from radicle.folio.db.models import FolioDraft, FolioNode
from radicle.folio.services import collab, ydoc
from radicle.platform.db.models import User
from tests.conftest import Team
from tests.integration.folio_helpers import API
from tests.unit.folio_docs import p, t


@pytest.fixture(autouse=True)
async def shared_session(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    @contextlib.asynccontextmanager
    async def shared() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(collab, "sessions", shared)
    yield
    await collab.rooms.close_all()


class Mem:
    """A peer whose 'socket' is its own Y.Doc."""

    def __init__(self, room: collab.Room, user: User) -> None:
        self.room = room
        self.doc: pycrdt.Doc[Any] = pycrdt.Doc()
        self.awareness = pycrdt.Awareness(pycrdt.Doc())
        self.peer = collab.Peer(send=self._receive, user=user)

    async def _receive(self, message: bytes) -> None:
        if message[0] == pycrdt.YMessageType.SYNC:
            reply = pycrdt.handle_sync_message(message[1:], self.doc)
            if reply is not None:
                asyncio.get_running_loop().create_task(self.room.receive(self.peer, reply))
        else:
            self.awareness.apply_awareness_update(pycrdt.read_message(message[1:]), None)

    async def say(self, text: str) -> None:
        before = self.doc.get_state()
        ydoc.append(ydoc.fragment(self.doc), [p(t(text))])
        update = self.doc.get_update(before)
        await self.room.receive(self.peer, pycrdt.create_update_message(update))

    def texts(self) -> list[str]:
        return [n["content"][0]["text"] for n in ydoc.to_json(self.doc)["content"]]


@pytest.fixture
async def node(client: AsyncClient, db: AsyncSession, team: Team) -> FolioNode:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Minuta"}
    )
    found = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert found is not None
    return found


async def _users(db: AsyncSession, team: Team) -> tuple[User, User]:
    member = await db.scalar(select(User).where(User.handle == team.member.handle))
    agent = await db.scalar(select(User).where(User.handle == team.agent.handle))
    assert member is not None and agent is not None
    return member, agent


async def _pending(db: AsyncSession, node: FolioNode) -> int:
    count = await db.scalar(
        select(func.count()).select_from(FolioYUpdate).where(FolioYUpdate.node_id == node.id)
    )
    return int(count or 0)


async def test_peers_converge_and_closing_compacts(
    db: AsyncSession, team: Team, node: FolioNode
) -> None:
    member, agent = await _users(db, team)
    room = await collab.rooms.open(db, node)
    a, b = Mem(room, member), Mem(room, agent)
    await room.join(a.peer)
    await room.join(b.peer)
    await a.say("uno")
    await b.say("dos")
    await asyncio.sleep(0.05)
    assert a.texts() == b.texts() and sorted(a.texts()) == ["dos", "uno"]
    assert await _pending(db, node) == 2 and room.authors == {member.id, agent.id}
    await collab.rooms.leave(room, a.peer)
    assert collab.rooms.get(node.id) is room  # b is still there
    await collab.rooms.leave(room, b.peer)
    assert collab.rooms.get(node.id) is None and await _pending(db, node) == 0
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None and len(draft.content_json["content"]) == 2


async def test_outside_changes_arrive_live_with_the_agents_label(
    db: AsyncSession, team: Team, node: FolioNode
) -> None:
    member, agent = await _users(db, team)
    room = await collab.rooms.open(db, node)
    a = Mem(room, member)
    await room.join(a.peer)
    await collab.apply_change(
        db, node, agent, lambda doc: ydoc.append(ydoc.fragment(doc), [p(t("del agente"))])
    )
    await asyncio.sleep(0.05)
    assert a.texts() == ["del agente"]
    labels = [s.get("user", {}) for s in a.awareness.states.values()]
    assert {"handle": team.agent.handle, "agent": True}.items() <= next(
        u for u in labels if u.get("handle")
    ).items()
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None and draft.content_json["content"] == [p(t("del agente"))]


async def test_outside_changes_without_a_room_are_stored(
    db: AsyncSession, team: Team, node: FolioNode
) -> None:
    _, agent = await _users(db, team)
    await collab.apply_change(
        db, node, agent, lambda doc: ydoc.append(ydoc.fragment(doc), [p(t("guardado"))])
    )
    assert await _pending(db, node) == 1
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None and draft.content_json["content"] == [p(t("guardado"))]


async def test_awareness_is_throttled_and_cleared_on_leave(
    db: AsyncSession, team: Team, node: FolioNode
) -> None:
    member, agent = await _users(db, team)
    room = await collab.rooms.open(db, node)
    a, b = Mem(room, member), Mem(room, agent)
    await room.join(a.peer)
    await room.join(b.peer)
    mine = pycrdt.Awareness(a.doc)
    for x in range(40):
        mine.set_local_state({"user": {"name": "Luis"}, "cursor": {"x": x}})
        update = mine.encode_awareness_update([a.doc.client_id])
        await room.receive(a.peer, pycrdt.create_awareness_message(update))
    state = b.awareness.states[a.doc.client_id]
    assert state["cursor"]["x"] == collab.AWARENESS_PER_SECOND - 1
    await collab.rooms.leave(room, a.peer)
    assert a.doc.client_id not in b.awareness.states


async def test_a_full_room(
    db: AsyncSession, team: Team, node: FolioNode, monkeypatch: pytest.MonkeyPatch
) -> None:
    member, agent = await _users(db, team)
    monkeypatch.setattr(collab, "MAX_PEERS", 1)
    room = await collab.rooms.open(db, node)
    await room.join(Mem(room, member).peer)
    assert room.full
    with pytest.raises(collab.RoomFull, match="editing this page"):
        await room.join(Mem(room, agent).peer)
