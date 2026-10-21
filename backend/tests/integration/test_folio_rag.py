"""The RAG index (Folio 1.6): publishing indexes, deleting and restricting update it,
reindexing is idempotent, and embeddings come from the configured provider."""

import json

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioChunk
from radicle.folio.services import rag
from radicle.platform.services import ai
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish

GUIDE = (
    "Intro corta.\n\n# Conecta un agente\n\nPasos para conectarlo.\n\n"
    "## Crea el agente\n\nVe a Admin, Agentes.\n\n| Campo | Valor |\n|---|---|\n| handle | bot |\n"
)


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    return r.json()


async def chunks(db: AsyncSession, node_id: str) -> list[FolioChunk]:
    rows = await db.scalars(
        select(FolioChunk).where(FolioChunk.node_id == node_id).order_by(FolioChunk.position)
    )
    return list(rows)


async def test_publishing_indexes_sections_with_metadata(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict
) -> None:
    await publish(client, team, page["id"], md=GUIDE)
    assert "folio_reindex_node" in await run_jobs(db)
    rows = await chunks(db, page["id"])
    assert [(c.heading_path, c.anchor) for c in rows] == [
        ([], None),
        (["Conecta un agente"], "conecta-un-agente"),
        (["Conecta un agente", "Crea el agente"], "crea-el-agente"),
    ]
    meta = rows[2].metadata_
    assert meta["space"] == "docs" and meta["doc_type"] == "how-to" and meta["version"] == 1
    assert meta["labels"] == ["mcp", "agentes"] and meta["restricted"] is False
    assert meta["url"].endswith("#crea-el-agente") and meta["author"] == "fernando"
    assert "| handle | bot |" in rows[2].text
    assert all(c.embedding is None for c in rows)  # no provider configured


async def test_reindexing_twice_gives_the_same_index(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict
) -> None:
    await publish(client, team, page["id"], md=GUIDE)
    await run_jobs(db)
    first = [(c.position, c.text) for c in await chunks(db, page["id"])]
    assert await rag.index_node(db, page["id"]) == 3
    assert [(c.position, c.text) for c in await chunks(db, page["id"])] == first


async def test_deleting_and_restricting_update_the_index(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict
) -> None:
    i = team.instance.headers
    await publish(client, team, page["id"], md=GUIDE)
    await run_jobs(db)
    r = await client.put(
        f"{API}/nodes/{page['id']}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": "fernando"}]},
    )
    assert r.status_code == 200
    await run_jobs(db)
    assert all(c.metadata_["restricted"] for c in await chunks(db, page["id"]))
    await client.delete(f"{API}/nodes/{page['id']}", headers=i)
    await run_jobs(db)
    assert await chunks(db, page["id"]) == []


async def test_embeddings_from_the_provider(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": n, "embedding": [0.1 * n, 1.0, 0.5]} for n, _ in enumerate(inputs)
                ]
            },
        )

    monkeypatch.setattr(ai, "transport", httpx.MockTransport(handler))
    await client.put(
        "/api/v1/admin/ai",
        headers=team.instance.headers,
        json={"provider": "openai", "embedding_model": "m", "api_key": "k"},
    )
    await publish(client, team, page["id"], md=GUIDE)
    await run_jobs(db)
    rows = await chunks(db, page["id"])
    assert all(c.embedding_dims == 3 and c.embedded_at for c in rows)
    assert list(rows[1].embedding) == pytest.approx([0.1, 1.0, 0.5])
    index = await db.scalar(
        text("SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_folio_chunks_embedding_3'")
    )
    assert index == 1


async def test_reembed_fills_in_missing_vectors(
    client: AsyncClient, db: AsyncSession, team: Team, page: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    await publish(client, team, page["id"], md=GUIDE)
    await run_jobs(db)
    assert await rag.reembed_missing(db) == 0  # no provider yet
    monkeypatch.setattr(
        ai,
        "transport",
        httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={"embeddings": [[1.0, 0.0] for _ in json.loads(r.content)["input"]]},
            )
        ),
    )
    await client.put(
        "/api/v1/admin/ai",
        headers=team.instance.headers,
        json={"provider": "ollama", "embedding_model": "nomic"},
    )
    assert await rag.reembed_missing(db) == 3
    missing = await db.scalar(
        select(func.count()).select_from(FolioChunk).where(FolioChunk.embedding.is_(None))
    )
    assert missing == 0
