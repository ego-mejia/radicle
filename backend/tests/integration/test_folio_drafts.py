"""Folio drafts (Folio 1.2): JSON from the editor, Markdown from agents, grouped history."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNodeEvent
from tests.conftest import Clock, Team
from tests.integration.folio_helpers import publish
from tests.unit.folio_docs import EVERY_BLOCK

API = "/api/v1/folio"


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    r = await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    assert r.status_code == 201, r.text
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    return r.json()


async def test_save_every_block_and_read_it_back(
    client: AsyncClient, team: Team, page: dict
) -> None:
    i = team.instance.headers
    url = f"{API}/nodes/{page['id']}/draft"
    empty = (await client.get(url, headers=i)).json()
    assert empty["saved"] is False and empty["content_json"] == {"type": "doc", "content": []}

    r = await client.put(
        url, headers=i, json={"content_json": EVERY_BLOCK, "metadata": {"labels": ["mcp"]}}
    )
    assert r.status_code == 200, r.text
    back = (await client.get(url, headers=i)).json()
    assert back["content_json"] == EVERY_BLOCK and back["saved"] is True
    assert back["metadata"] == {"labels": ["mcp"]}
    assert back["content_md"].startswith("# Conecta un agente\n")

    # Metadata alone keeps the content.
    await client.put(url, headers=i, json={"metadata": {"description": "x"}})
    assert (await client.get(url, headers=i)).json()["content_json"] == EVERY_BLOCK


async def test_markdown_from_agents(client: AsyncClient, team: Team, page: dict) -> None:
    url = f"{API}/nodes/{page['id']}/draft"
    r = await client.put(
        url,
        headers=team.instance.headers,
        json={"content_md": "# Hola\n\n:::panel{kind=tip}\nOjo\n:::\n"},
    )
    assert [b["type"] for b in r.json()["content_json"]["content"]] == ["heading", "panel"]


async def test_history_groups_an_editing_session(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict, clock: Clock
) -> None:
    url = f"{API}/nodes/{page['id']}/draft"
    for _ in range(3):
        await client.put(url, headers=team.instance.headers, json={"content_md": "uno"})
    clock.advance(minutes=11)
    await client.put(url, headers=team.instance.headers, json={"content_md": "dos"})
    saved = await db.scalars(
        select(FolioNodeEvent.event_type).where(
            FolioNodeEvent.node_id == page["id"], FolioNodeEvent.event_type == "draft_saved"
        )
    )
    assert len(list(saved)) == 2


async def test_actionable_errors(client: AsyncClient, team: Team, page: dict) -> None:
    i = team.instance.headers
    url = f"{API}/nodes/{page['id']}/draft"
    bad = {"type": "doc", "content": [{"type": "script"}]}
    r = await client.put(url, headers=i, json={"content_json": bad})
    assert r.status_code == 422 and "$.content[0]" in r.json()["detail"]
    r = await client.put(url, headers=i, json={"content_json": EVERY_BLOCK, "content_md": "x"})
    assert r.status_code == 422 and "not both" in r.json()["detail"]
    r = await client.put(url, headers=i, json={"metadata": {str(n): n for n in range(51)}})
    assert r.status_code == 422
    folder = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "folder", "title": "F"}
    )
    r = await client.get(f"{API}/nodes/{folder.json()['id']}/draft", headers=i)
    assert r.status_code == 422 and "Folders have no content" in r.json()["detail"]


async def test_readers_cannot_read_or_write_drafts(
    client: AsyncClient, team: Team, page: dict
) -> None:
    url = f"{API}/nodes/{page['id']}/draft"
    # Unpublished pages don't exist for readers; published ones they read but don't edit.
    assert (await client.get(url, headers=team.member.headers)).status_code == 404
    await publish(client, team, page["id"])
    assert (await client.get(url, headers=team.member.headers)).status_code == 403
    r = await client.put(url, headers=team.member.headers, json={"content_md": "x"})
    assert r.status_code == 403
