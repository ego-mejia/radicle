"""Where collaborative documents live (Folio 2.2): seeding, updates, compaction and the
draft's JSON."""

import uuid

import pycrdt
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioYUpdate
from radicle.folio.db.models import FolioDraft, FolioNode
from radicle.folio.services import ydoc, ystore
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish
from tests.unit.folio_docs import p, t


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


async def _pending(db: AsyncSession, node: FolioNode) -> int:
    count = await db.scalar(
        select(func.count()).select_from(FolioYUpdate).where(FolioYUpdate.node_id == node.id)
    )
    return int(count or 0)


async def test_seeded_once_from_the_published_page(
    client: AsyncClient, db: AsyncSession, team: Team, node: FolioNode
) -> None:
    await publish(client, team, str(node.id), md="# Hola\n\nPrimera versión.")
    first = await ystore.load(db, node)
    second = await ystore.load(db, node)
    assert ydoc.to_json(first) == ydoc.to_json(second)
    assert ydoc.to_json(first)["content"][0]["type"] == "heading"
    # The same structure, not a second copy: an update from one applies cleanly to the other.
    ydoc.append(ydoc.fragment(first), [p(t("nuevo"))])
    second.apply_update(first.get_update(second.get_state()))
    assert len(ydoc.to_json(second)["content"]) == 3


async def test_updates_replay_and_compact(db: AsyncSession, node: FolioNode) -> None:
    doc = await ystore.load(db, node)
    before = doc.get_state()
    ydoc.append(ydoc.fragment(doc), [p(t("uno"))])
    await ystore.append_update(db, node.id, doc.get_update(before))
    before = doc.get_state()
    ydoc.append(ydoc.fragment(doc), [p(t("dos"))])
    await ystore.append_update(db, node.id, doc.get_update(before))
    assert await _pending(db, node) == 2
    reloaded = await ystore.load(db, node)
    assert ydoc.to_json(reloaded) == ydoc.to_json(doc)
    assert await ystore.compact(db, node.id, reloaded) == 2
    assert await _pending(db, node) == 0
    assert ydoc.to_json(await ystore.load(db, node)) == ydoc.to_json(doc)


async def test_the_draft_follows_the_ydoc(db: AsyncSession, node: FolioNode) -> None:
    doc = await ystore.load(db, node)
    ydoc.append(ydoc.fragment(doc), [p(t("Acuerdos"))])
    assert await ystore.save_json(db, node, doc)
    draft = await db.get(FolioDraft, node.id)
    assert draft is not None and draft.content_json == {
        "type": "doc",
        "content": [p(t("Acuerdos"))],
    }
    # Something the schema rejects keeps the last valid content.
    ydoc.fragment(doc).children.append(pycrdt.XmlElement("columns", {"layout": "two"}))
    assert not await ystore.save_json(db, node, doc)
    await db.refresh(draft)
    assert draft.content_json["content"] == [p(t("Acuerdos"))]
