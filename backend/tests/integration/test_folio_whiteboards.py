"""Whiteboards (Folio 3.5): two people draw on the same scene, the room keeps its JSON
and its text, readers get it over REST and only editors draw."""

import contextlib
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.whiteboards import FolioWhiteboard
from radicle.folio.services import collab, whiteboards
from tests.conftest import Team, run_jobs
from tests.integration.collab_ws import Rejected, YClient, connected, settle
from tests.integration.folio_helpers import API


@pytest.fixture(autouse=True)
async def rooms(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    @contextlib.asynccontextmanager
    async def shared() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(collab, "sessions", shared)
    monkeypatch.setattr(collab, "SAVE_EVERY", 0.05)
    yield
    await collab.rooms.close_all()


@pytest.fixture
async def board(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "whiteboard", "title": "Mapa"}
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _element(id: str, index: str, **extra: Any) -> dict[str, Any]:
    return {"id": id, "type": "rectangle", "index": index, "version": 1, **extra}


def _draw(y: YClient, element: dict[str, Any]) -> None:
    whiteboards.elements_map(y.doc)[element["id"]] = element


def _ids(y: YClient) -> list[str]:
    return [e["id"] for e in whiteboards.read(y.doc)]


async def test_two_people_draw_together_and_the_scene_is_kept(
    client: AsyncClient, db: AsyncSession, team: Team, board: str
) -> None:
    async with (
        connected(client, board, team.instance.headers) as a,
        connected(client, board, team.instance.headers) as b,
    ):
        _draw(a, _element("box", "a1"))
        _draw(b, _element("note", "a2", type="text", text="Servicio de pagos"))
        await settle(lambda: _ids(a) == _ids(b) == ["box", "note"])
        _draw(b, _element("box", "a1", version=2, isDeleted=True))
        await settle(lambda: _ids(a) == ["note"])
        room = collab.rooms.get(uuid.UUID(board))
        assert room is not None
        await room.save()
    row = await db.get(FolioWhiteboard, uuid.UUID(board), populate_existing=True)
    assert row is not None
    assert [e["id"] for e in row.elements] == ["note"]
    assert row.text == "Servicio de pagos"
    # Back later: the room starts from what was kept.
    async with connected(client, board, team.instance.headers) as c:
        await settle(lambda: _ids(c) == ["note"])


async def _saved_on_server(board: str, done: Any) -> None:
    """Wait for the server's copy, then save it: the save on disconnect runs after the room
    is gone, so a test that only leaves could look for the reindex job too early."""
    room = collab.rooms.get(uuid.UUID(board))
    assert room is not None
    await settle(lambda: done(whiteboards.read(room.doc)))
    await room.save()


async def test_its_text_is_found_by_search(
    client: AsyncClient, db: AsyncSession, team: Team, board: str
) -> None:
    async with connected(client, board, team.instance.headers) as a:
        _draw(a, _element("note", "a1", type="text", text="Cola de facturación"))
        await _saved_on_server(board, lambda els: [e["id"] for e in els] == ["note"])
    await run_jobs(db)
    r = await client.get(
        f"{API}/search", params={"q": "facturación", "mode": "text"}, headers=team.member.headers
    )
    assert r.status_code == 200, r.text
    hits = r.json()["items"]
    assert [h["node_id"] for h in hits] == [board] and "facturación" in hits[0]["snippet"]
    # Erasing the text takes it out of the index.
    async with connected(client, board, team.instance.headers) as b:
        # Erase it once b has it: a write before the sync is concurrent, and Yjs may keep
        # the other client's version of the key.
        await settle(lambda: _ids(b) == ["note"])
        _draw(b, _element("note", "a1", type="text", text="", version=2, isDeleted=True))
        await _saved_on_server(board, lambda els: els == [])
    await run_jobs(db)
    r = await client.get(
        f"{API}/search", params={"q": "facturación", "mode": "text"}, headers=team.member.headers
    )
    assert r.json()["items"] == []


async def test_readers_get_the_scene_over_rest(client: AsyncClient, team: Team, board: str) -> None:
    async with connected(client, board, team.instance.headers) as a:
        _draw(a, _element("box", "a1"))
        await settle(lambda: collab.rooms.get(uuid.UUID(board)) is not None)
        room = collab.rooms.get(uuid.UUID(board))
        await settle(lambda: room is not None and whiteboards.read(room.doc) != [])
        r = await client.get(f"{API}/whiteboards/{board}", headers=team.member.headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["title"] == "Mapa" and body["space"] == "docs" and not body["can_edit"]
        assert [e["id"] for e in body["elements"]] == ["box"]
    mine = await client.get(f"{API}/whiteboards/{board}", headers=team.instance.headers)
    assert mine.json()["can_edit"] and [e["id"] for e in mine.json()["elements"]] == ["box"]


async def test_errors_and_permissions(client: AsyncClient, team: Team, board: str) -> None:
    i = team.instance.headers
    page = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    r = await client.get(f"{API}/whiteboards/{page.json()['id']}", headers=i)
    assert r.status_code == 422 and "not a whiteboard" in r.json()["detail"]
    r = await client.get(f"{API}/whiteboards/{uuid.uuid4()}", headers=i)
    assert r.status_code == 404
    with pytest.raises(Rejected) as rejected:
        async with connected(client, board, team.member.headers):  # reads, doesn't draw
            pass
    assert rejected.value.code == 4403


def test_reading_a_scene() -> None:
    doc = whiteboards.from_elements(
        [
            _element("b", "a2", type="frame", name="Backend"),
            _element("a", "a1", type="text", text="  API  "),
            _element("gone", "a0", isDeleted=True),
            {"type": "rectangle"},  # no id: left out
        ]
    )
    elements = whiteboards.read(doc)
    assert [e["id"] for e in elements] == ["a", "b"]
    assert whiteboards.text_of(elements) == "API\nBackend"
