"""The RAG index (Folio 1.6): the chunks of each node's published version, with flat
metadata for filters and an embedding when an AI provider is configured.

`folio_reindex_node` is idempotent: it deletes the node's chunks and writes them again from
what is published now, so the index always mirrors the last published, live version.
It runs after publishing, restoring, moving, deleting and changing restrictions.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import delete, exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioChunk,
    FolioNode,
    FolioPageRestriction,
    FolioSpace,
    FolioVersion,
    RestrictionMode,
)
from radicle.folio.services import chunking
from radicle.platform.db.models import User, utcnow
from radicle.platform.services import ai, queue

log = logging.getLogger("radicle.folio.rag")

REINDEX_JOB = "folio_reindex_node"
BATCH = 64


async def schedule(db: AsyncSession, node_ids: list[uuid.UUID]) -> None:
    """Queue a reindex for each node; a reindex already waiting covers a new request."""
    for node_id in node_ids:
        await queue.enqueue(
            db, REINDEX_JOB, queueing_lock=f"folio-reindex-{node_id}", node_id=str(node_id)
        )


async def subtree(db: AsyncSession, node: FolioNode) -> list[uuid.UUID]:
    """The node and everything under it."""
    tree = select(FolioNode.id).where(FolioNode.id == node.id).cte("subtree", recursive=True)
    tree = tree.union_all(select(FolioNode.id).where(FolioNode.parent_id == tree.c.id))
    return list(await db.scalars(select(tree.c.id)))


async def _ancestry(db: AsyncSession, node: FolioNode) -> list[FolioNode]:
    chain = [node]
    while chain[-1].parent_id is not None:
        parent = await db.get(FolioNode, chain[-1].parent_id)
        if parent is None:
            break
        chain.append(parent)
    return chain


async def _restricted(db: AsyncSession, chain: list[FolioNode]) -> bool:
    found = await db.scalar(
        select(
            exists().where(
                FolioPageRestriction.node_id.in_([n.id for n in chain]),
                FolioPageRestriction.mode == RestrictionMode.view,
            )
        )
    )
    return bool(found)


async def _embeddings(texts: list[str], db: AsyncSession) -> list[list[float]] | None:
    """Vectors for the texts, or None without a provider or when it fails (search then
    falls back to full text; `radicle folio reembed` fills them in later)."""
    cfg = await ai.load(db)
    if not cfg.enabled or not cfg.embedding_model:
        return None
    vectors: list[list[float]] = []
    try:
        for start in range(0, len(texts), BATCH):
            vectors += await ai.embed_many(cfg, texts[start : start + BATCH])
    except ai.AiUnavailable as exc:
        log.warning("Folio embeddings skipped: %s", exc.detail)
        return None
    return vectors


async def ensure_index(db: AsyncSession, dims: int) -> None:
    """One HNSW index per embedding dimension (ADR 0037)."""
    if not 1 <= dims <= ai.MAX_DIMENSIONS:
        return
    await db.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_folio_chunks_embedding_{dims} ON folio_chunks "
            f"USING hnsw ((embedding::vector({dims})) vector_cosine_ops) "
            f"WHERE embedding_dims = {dims}"
        )
    )


async def index_node(db: AsyncSession, node_id: uuid.UUID) -> int:
    """Rebuild the node's chunks; returns how many there are now."""
    await db.execute(delete(FolioChunk).where(FolioChunk.node_id == node_id))
    node = await db.get(FolioNode, node_id)
    if node is None or node.published_version_id is None:
        return 0
    space = await db.get(FolioSpace, node.space_id)
    chain = await _ancestry(db, node)
    if space is None or space.deleted_at is not None or any(n.deleted_at for n in chain):
        return 0
    version = await db.get(FolioVersion, node.published_version_id)
    if version is None:  # pragma: no cover - the published version always exists
        return 0
    author = await db.get(User, version.author_id)
    meta = version.metadata_
    base: dict[str, Any] = {
        "space": space.key,
        "node_kind": node.kind.value,
        "doc_type": meta.get("doc_type"),
        "labels": meta.get("labels", []),
        "audiences": meta.get("audiences", []),
        "language": meta.get("language"),
        "owner": meta.get("owner"),
        "author": author.handle if author else None,
        "version": version.number,
        "published_at": node.published_at.isoformat() if node.published_at else None,
        "title": version.title,
        "description": meta.get("description", ""),
        "restricted": await _restricted(db, chain),
    }
    chunks = chunking.chunk(version.content_json)
    inputs = [chunking.embedding_input(version.title, base["description"], c) for c in chunks]
    vectors = await _embeddings(inputs, db) if chunks else None
    url = f"/folio/p/{node.id}-{node.slug}"
    for i, c in enumerate(chunks):
        vector = vectors[i] if vectors else None
        db.add(
            FolioChunk(
                node_id=node.id,
                version_id=version.id,
                position=c.position,
                heading_path=c.heading_path,
                anchor=c.anchor,
                text=c.text,
                token_count=c.token_count,
                metadata_={
                    **base,
                    "section": " > ".join(c.heading_path),
                    "url": f"{url}#{c.anchor}" if c.anchor else url,
                },
                embedding=vector,
                embedding_dims=len(vector) if vector else None,
                embedded_at=utcnow() if vector else None,
            )
        )
    await db.flush()
    if vectors:
        await ensure_index(db, len(vectors[0]))
    return len(chunks)


@queue.handler(REINDEX_JOB)
async def reindex_node(db: AsyncSession, node_id: str, **_: Any) -> None:
    await index_node(db, uuid.UUID(node_id))


async def reembed_missing(db: AsyncSession) -> int:
    """Embed the chunks that don't have a vector of the current model's dimension yet."""
    cfg = await ai.load(db)
    if not cfg.enabled or not cfg.embedding_model:
        return 0
    rows = list(await db.scalars(select(FolioChunk).where(FolioChunk.embedding.is_(None))))
    done = 0
    for start in range(0, len(rows), BATCH):
        batch = rows[start : start + BATCH]
        inputs = []
        for c in batch:
            meta = c.metadata_
            piece = chunking.Chunk(c.position, c.heading_path, c.anchor, c.text, c.token_count)
            inputs.append(
                chunking.embedding_input(meta.get("title", ""), meta.get("description", ""), piece)
            )
        vectors = await ai.embed_many(cfg, inputs)
        for c, vector in zip(batch, vectors, strict=True):
            c.embedding, c.embedding_dims, c.embedded_at = vector, len(vector), utcnow()
            done += 1
        await db.flush()
        await ensure_index(db, len(vectors[0]))
    return done
