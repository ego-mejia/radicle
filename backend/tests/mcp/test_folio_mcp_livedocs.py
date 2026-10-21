"""Live docs over REST and MCP (Folio 2.5): snapshots, restoring, appending, and an agent
appending while people write."""

import contextlib
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import collab, ydoc
from tests.conftest import Clock, Team
from tests.integration.collab_ws import connected, settle
from tests.integration.folio_helpers import API, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload
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
async def space(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    await agent_can_write(client, team, "docs")
    return "docs"


async def _minuta(client: AsyncClient, team: Team) -> str:
    r = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": "docs", "kind": "live_doc", "title": "Daily"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def test_rest_snapshots_restore_and_append(
    client: AsyncClient, team: Team, space: str, clock: Clock
) -> None:
    i = team.instance.headers
    node = await _minuta(client, team)
    r = await client.post(f"{API}/nodes/{node}/append", headers=i, json={"content_md": "Uno."})
    assert r.status_code == 200 and r.json()["content_md"].strip() == "Uno."
    clock.advance(minutes=11)
    await client.post(f"{API}/nodes/{node}/append", headers=i, json={"content_md": "Dos."})
    history = (await client.get(f"{API}/nodes/{node}/snapshots", headers=i)).json()["items"]
    assert len(history) == 2 and history[0]["authors"] == [team.instance.handle]
    first = history[1]["id"]
    one = (await client.get(f"{API}/nodes/{node}/snapshots/{first}", headers=i)).json()
    assert one["content_md"].strip() == "Uno."
    r = await client.post(f"{API}/nodes/{node}/snapshots/{first}/restore", headers=i)
    assert r.status_code == 201, r.text
    page = (await client.get(f"{API}/nodes/{node}", headers=i)).json()
    assert page["content_json"] == {"type": "doc", "content": [p(t("Uno."))]}


async def test_rest_errors_and_permissions(client: AsyncClient, team: Team, space: str) -> None:
    node = await _minuta(client, team)
    body = {"content_md": "x"}
    r = await client.post(f"{API}/nodes/{node}/append", headers=team.viewer.headers, json=body)
    assert r.status_code == 403
    r = await client.get(
        f"{API}/nodes/{node}/snapshots/{uuid.uuid4()}", headers=team.viewer.headers
    )
    assert r.status_code == 404
    page = await client.post(
        f"{API}/nodes",
        headers=team.instance.headers,
        json={"space": "docs", "kind": "page", "title": "Normal"},
    )
    url = f"{API}/nodes/{page.json()['id']}/snapshots"
    r = await client.get(url, headers=team.instance.headers)
    assert r.status_code == 422 and "not a live doc" in r.json()["detail"]


async def test_mcp_creates_and_appends_without_overwriting_people(
    client: AsyncClient, team: Team, space: str
) -> None:
    async with folio_mcp(client, team.agent) as folio:
        made = payload(
            await folio.call_tool(
                "create_live_doc",
                {"space": "docs", "title": "Daily del agente", "content_md": "# Agenda"},
            )
        )
        r = await client.get(f"{API}/nodes/{made['id']}", headers=team.member.headers)
        assert r.json()["content_json"]["content"][0]["type"] == "heading"

        async with connected(client, made["id"], team.instance.headers) as person:
            ydoc.append(ydoc.fragment(person.doc), [p(t("Escrito por una persona"))])
            room = collab.rooms.get(uuid.UUID(made["id"]))
            assert room is not None
            await settle(lambda: len(ydoc.to_json(room.doc)["content"]) == 2)
            out = payload(
                await folio.call_tool(
                    "append_to_live_doc", {"id": made["id"], "content_md": "## Acuerdos"}
                )
            )
            assert (
                "Escrito por una persona" in out["content_md"] and "Acuerdos" in out["content_md"]
            )
            await settle(lambda: len(person.json()["content"]) == 3)
        text = error_text(
            await folio.call_tool(
                "append_to_live_doc", {"id": str(uuid.uuid4()), "content_md": "x"}
            )
        )
        assert "not found" in text.lower()
