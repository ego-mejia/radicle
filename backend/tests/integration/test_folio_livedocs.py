"""Live docs (Folio 2.5): always editable, never published, readable as they are written,
with a snapshot every 10 minutes with changes."""

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import collab, livedocs
from radicle.platform.db.models import User
from tests.conftest import Clock, Team
from tests.integration.folio_helpers import API
from tests.integration.test_folio_room import Mem
from tests.unit.folio_docs import p, t


@pytest.fixture(autouse=True)
async def shared_session(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    @contextlib.asynccontextmanager
    async def shared() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(collab, "sessions", shared)
    yield
    await collab.rooms.close_all()


@pytest.fixture
async def minuta(client: AsyncClient, db: AsyncSession, team: Team) -> FolioNode:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes",
        headers=i,
        json={"space": "docs", "kind": "live_doc", "title": "Daily del lunes"},
    )
    assert r.status_code == 201, r.text
    found = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert found is not None
    return found


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


async def test_readers_see_it_as_written_and_it_never_publishes(
    client: AsyncClient, db: AsyncSession, team: Team, minuta: FolioNode
) -> None:
    admin = await _user(db, team.instance.handle)
    await livedocs.append(db, admin, minuta, "# Acuerdos\n\nSubir el release el jueves.")
    seen = await client.get(f"{API}/nodes/{minuta.id}", headers=team.member.headers)
    assert seen.status_code == 200, seen.text
    body = seen.json()
    assert body["kind"] == "live_doc" and body["version"] is None
    assert body["content_json"]["content"][0]["type"] == "heading"
    r = await client.post(
        f"{API}/nodes/{minuta.id}/publish", headers=team.instance.headers, json={}
    )
    assert r.status_code == 422 and "never published" in r.json()["detail"]
    tree = (await client.get(f"{API}/spaces/docs/tree", headers=team.member.headers)).json()
    assert [n["kind"] for n in tree] == ["live_doc"]


async def test_snapshots_every_ten_minutes_with_changes(
    db: AsyncSession, team: Team, minuta: FolioNode, clock: Clock
) -> None:
    admin = await _user(db, team.instance.handle)
    await livedocs.append(db, admin, minuta, "Primer punto.")
    await livedocs.append(db, admin, minuta, "Segundo punto.")
    assert len(await livedocs.snapshots(db, minuta)) == 1  # within 10 minutes: one
    clock.advance(minutes=11)
    await livedocs.append(db, admin, minuta, "Tercer punto.")
    history = await livedocs.snapshots(db, minuta)
    assert len(history) == 2 and history[0].authors == [admin.id]
    assert len(history[0].content_json["content"]) == 3


async def test_a_room_snapshots_who_wrote(db: AsyncSession, team: Team, minuta: FolioNode) -> None:
    luis, agent = await _user(db, team.member.handle), await _user(db, team.agent.handle)
    room = await collab.rooms.open(db, minuta)
    assert room.live
    a, b = Mem(room, luis), Mem(room, agent)
    await room.join(a.peer)
    await room.join(b.peer)
    await a.say("de Luis")
    await b.say("del agente")
    await asyncio.sleep(0.02)
    await room.snapshot()
    await room.snapshot()  # nothing changed since: no second one
    history = await livedocs.snapshots(db, minuta)
    assert len(history) == 1 and set(history[0].authors) == {luis.id, agent.id}
    await a.say("antes de cerrar")
    await collab.rooms.leave(room, a.peer)
    await collab.rooms.leave(room, b.peer)  # closing takes the last one
    assert len(await livedocs.snapshots(db, minuta)) == 2


async def test_restore_brings_back_a_snapshot_as_a_new_one(
    db: AsyncSession, team: Team, minuta: FolioNode, clock: Clock
) -> None:
    admin = await _user(db, team.instance.handle)
    await livedocs.append(db, admin, minuta, "Versión buena.")
    first = (await livedocs.snapshots(db, minuta))[0]
    clock.advance(minutes=11)
    await livedocs.append(db, admin, minuta, "Algo que sobra.")
    restored = await livedocs.restore(db, admin, minuta, first.id)
    assert restored.id != first.id and restored.content_json == first.content_json
    doc = await collab.current(db, minuta)
    from radicle.folio.services import ydoc

    assert ydoc.to_json(doc) == {"type": "doc", "content": [p(t("Versión buena."))]}
    assert len(await livedocs.snapshots(db, minuta)) == 3


async def test_errors(client: AsyncClient, db: AsyncSession, team: Team, minuta: FolioNode) -> None:
    admin = await _user(db, team.instance.handle)
    r = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": "docs", "kind": "page", "title": "Página normal"},
    )
    page = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert page is not None
    with pytest.raises(Exception, match="not a live doc"):
        await livedocs.append(db, admin, page, "x")
    with pytest.raises(Exception, match="Nothing to append"):
        await livedocs.append(db, admin, minuta, "   ")
    with pytest.raises(Exception, match="not found"):
        await livedocs.get_snapshot(db, minuta, uuid.uuid4())
    viewer = await _user(db, team.viewer.handle)
    with pytest.raises(Exception, match="can't edit"):
        await livedocs.append(db, viewer, minuta, "x")
