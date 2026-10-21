"""Real-time editing (Folio 2.2): clients converge, the room stores and compacts, only
editors connect, agents' changes arrive labelled, and awareness is throttled."""

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioYUpdate
from radicle.folio.db.models import FolioDraft, FolioNode
from radicle.folio.services import collab, ydoc
from radicle.platform.db.models import User
from tests.conftest import Team
from tests.integration.collab_ws import Rejected, YClient, connected, settle
from tests.integration.folio_helpers import API, METADATA, publish
from tests.unit.folio_docs import p, t


@pytest.fixture(autouse=True)
async def rooms(db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    @contextlib.asynccontextmanager
    async def shared() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(collab, "sessions", shared)
    monkeypatch.setattr(collab, "SAVE_EVERY", 0.05)
    monkeypatch.setattr(collab, "COMPACT_EVERY", 0.2)
    yield
    await collab.rooms.close_all()


async def _writer(client: AsyncClient, team: Team, handle: str) -> None:
    i = team.instance.headers
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": handle, "role": "creator"},
    )
    assert r.status_code == 201, r.text
    grants = (await client.get(f"{API}/spaces/docs/grants", headers=i)).json()["grants"]
    grants.append({"grantee_type": "user", "grantee": handle, "permissions": ["view", "create"]})
    r = await client.put(f"{API}/spaces/docs/grants", headers=i, json={"grants": grants})
    assert r.status_code == 200, r.text


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Minuta"}
    )
    for actor in (team.member, team.agent):
        await _writer(client, team, actor.handle)
    return str(r.json()["id"])


def _say(y: YClient, text: str) -> None:
    ydoc.append(ydoc.fragment(y.doc), [p(t(text))])


def _texts(y: YClient) -> list[str]:
    return [n["content"][0]["text"] for n in y.json()["content"] if n.get("content")]


async def _pending(db: AsyncSession, node: str) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(FolioYUpdate)
        .where(FolioYUpdate.node_id == uuid.UUID(node))
    )
    return int(count or 0)


async def test_three_clients_converge_and_the_draft_follows(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    async with (
        connected(client, page, team.instance.headers) as a,
        connected(client, page, team.member.headers) as b,
        connected(client, page, team.agent.headers) as c,
    ):
        _say(a, "uno")
        _say(b, "dos")
        _say(c, "tres")
        await settle(lambda: all(sorted(_texts(y)) == ["dos", "tres", "uno"] for y in (a, b, c)))
        assert a.json() == b.json() == c.json()
        room = collab.rooms.get(uuid.UUID(page))
        assert room is not None and len(room.peers) == 3
        await room.save()
    draft = await db.get(FolioDraft, uuid.UUID(page))
    assert draft is not None
    assert sorted(n["content"][0]["text"] for n in draft.content_json["content"]) == [
        "dos",
        "tres",
        "uno",
    ]


async def test_reconnecting_loses_nothing_and_closing_compacts(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    async with connected(client, page, team.member.headers) as a:
        _say(a, "antes de irme")
        await settle(lambda: collab.rooms.get(uuid.UUID(page)) is not None)
        room = collab.rooms.get(uuid.UUID(page))
        assert room is not None
        await settle(lambda: bool(room is not None and _room_texts(room)))
    assert collab.rooms.get(uuid.UUID(page)) is None  # the last one left: closed
    assert await _pending(db, page) == 0  # compacted
    async with connected(client, page, team.instance.headers) as b:
        await settle(lambda: _texts(b) == ["antes de irme"])


def _room_texts(room: collab.Room) -> list[str]:
    return [n["content"][0]["text"] for n in ydoc.to_json(room.doc)["content"]]


async def test_only_editors_connect(client: AsyncClient, team: Team, page: str) -> None:
    await publish(client, team, page)  # readers can see it, but not edit it
    for headers, code in (
        (team.viewer.headers, 4403),  # a reader
        ({}, 4401),
        ({"Authorization": "Bearer rdc_nope"}, 4401),
    ):
        with pytest.raises(Rejected) as rejected:
            async with connected(client, page, headers):
                pass
        assert rejected.value.code == code
    with pytest.raises(Rejected) as rejected:
        async with connected(client, str(uuid.uuid4()), team.member.headers):
            pass
    assert rejected.value.code == 4404


async def test_an_agent_edit_arrives_labelled(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    agent = await db.scalar(select(User).where(User.handle == team.agent.handle))
    node = await db.get(FolioNode, uuid.UUID(page))
    assert agent is not None and node is not None
    async with connected(client, page, team.member.headers) as a:
        await collab.apply_change(
            db, node, agent, lambda doc: ydoc.append(ydoc.fragment(doc), [p(t("del agente"))])
        )
        await settle(lambda: _texts(a) == ["del agente"])
        await settle(
            lambda: any(
                (s.get("user") or {}).get("handle") == team.agent.handle
                for s in a.peer_awareness.states.values()
            )
        )
    draft = await db.get(FolioDraft, uuid.UUID(page))
    assert draft is not None and draft.content_json["content"] == [p(t("del agente"))]


async def test_change_without_a_room_is_stored(db: AsyncSession, team: Team, page: str) -> None:
    agent = await db.scalar(select(User).where(User.handle == team.agent.handle))
    node = await db.get(FolioNode, uuid.UUID(page))
    assert agent is not None and node is not None
    await collab.apply_change(
        db, node, agent, lambda doc: ydoc.append(ydoc.fragment(doc), [p(t("guardado"))])
    )
    assert await _pending(db, page) == 1
    draft = await db.get(FolioDraft, uuid.UUID(page))
    assert draft is not None and draft.content_json["content"] == [p(t("guardado"))]


async def test_awareness_is_throttled_and_relayed(
    client: AsyncClient, team: Team, page: str
) -> None:
    async with (
        connected(client, page, team.member.headers) as a,
        connected(client, page, team.agent.headers) as b,
    ):
        for n in range(40):
            await a.set_awareness({"user": {"name": "Luis"}, "cursor": {"x": n, "y": 1}})
        last = collab.AWARENESS_PER_SECOND - 1
        states = b.peer_awareness.states
        await settle(lambda: (states.get(a.doc.client_id) or {}).get("cursor", {}).get("x") == last)
        await asyncio.sleep(0.2)  # nothing past the limit arrives later
        state = states[a.doc.client_id]
        assert state["user"] == {"name": "Luis"} and state["cursor"]["x"] == last


async def test_a_full_room_says_so(
    client: AsyncClient, team: Team, page: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(collab, "MAX_PEERS", 1)
    async with connected(client, page, team.member.headers):
        await settle(lambda: bool((room := collab.rooms.get(uuid.UUID(page))) and room.peers))
        with pytest.raises(Rejected) as rejected:
            async with connected(client, page, team.agent.headers):
                pass
    assert rejected.value.code == 4429 and "editing this page" in rejected.value.reason


async def test_an_agent_draft_over_rest_shows_up_live(
    client: AsyncClient, team: Team, page: str
) -> None:
    async with connected(client, page, team.member.headers) as a:
        r = await client.put(
            f"{API}/nodes/{page}/draft",
            headers=team.agent.headers,
            json={"content_md": "# Resumen\n\nLo escribió el agente."},
        )
        assert r.status_code == 200, r.text
        await settle(lambda: [n["type"] for n in a.json()["content"]] == ["heading", "paragraph"])
        await settle(
            lambda: any(
                (s.get("user") or {}).get("agent") for s in a.peer_awareness.states.values()
            )
        )


async def test_publishing_takes_what_is_on_screen(
    client: AsyncClient, team: Team, page: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(collab, "SAVE_EVERY", 60)  # no autosave: only the flush counts
    i = team.instance.headers
    r = await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"metadata": METADATA})
    assert r.status_code == 200, r.text
    async with connected(client, page, team.member.headers) as a:
        _say(a, "recién escrito")
        await settle(lambda: bool((room := collab.rooms.get(uuid.UUID(page))) and room.authors))
        r = await client.post(f"{API}/nodes/{page}/publish", headers=i, json={})
        assert r.status_code == 201, r.text
    version = (await client.get(f"{API}/nodes/{page}/versions/1", headers=i)).json()
    assert "recién escrito" in version["content_md"]
