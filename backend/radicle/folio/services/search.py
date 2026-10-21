"""Searching Folio (Folio 1.6): full text in English and Spanish, semantic with the AI
provider's embeddings, and hybrid (the default) fusing both with Reciprocal Rank Fusion.

The visibility rule goes into the SQL of every query, before ranking: a page you may not
see never takes a slot, a rank or a snippet.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any, Literal

from pgvector.sqlalchemy import Vector
from sqlalchemy import ColumnElement, Float, Text, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioChunk, FolioNode
from radicle.folio.services import access
from radicle.platform.db.models import User
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import ai

Mode = Literal["hybrid", "text", "semantic"]
RRF_K = 60
CANDIDATES = 50
SEMANTIC_TOP = 20
# Verified docs rise a little and outdated ones sink (Folio 2.7).
BOOST = {"verified": 1.15, "outdated": 0.85}
MARKUP = r"[*`|#>~_]+|-{3,}|:{3,}\S*"
SNIPPET = "StartSel=**,StopSel=**,MaxWords=30,MinWords=12,MaxFragments=1"


@dataclass(frozen=True)
class Filters:
    space: str | None = None
    kind: str | None = None
    doc_type: str | None = None
    label: str | None = None
    author: str | None = None
    owner: str | None = None
    audience: str | None = None
    language: str | None = None
    published_from: date | None = None
    published_to: date | None = None


@dataclass
class Hit:
    node_id: uuid.UUID
    title: str
    description: str
    heading_path: list[str]
    anchor: str | None
    url: str
    snippet: str
    space: str
    doc_type: str | None
    status: str = "published"
    score: float = 0.0
    matched_by: list[str] = field(default_factory=list)


def _meta(key: str) -> Any:
    return FolioChunk.metadata_[key].astext


def _where(f: Filters) -> list[ColumnElement[bool]]:
    """Filters on the chunks' flat metadata."""
    clauses: list[ColumnElement[bool]] = []
    exact = {"space": f.space, "doc_type": f.doc_type, "language": f.language, "node_kind": f.kind}
    clauses += [_meta(key) == value for key, value in exact.items() if value]
    people = {"author": f.author, "owner": f.owner}
    clauses += [_meta(key) == value.lstrip("@").lower() for key, value in people.items() if value]
    lists = {"labels": f.label and f.label.lstrip("#").lower(), "audiences": f.audience}
    clauses += [
        FolioChunk.metadata_[key].contains(cast([value], JSONB))
        for key, value in lists.items()
        if value
    ]
    if f.published_from:
        start = datetime.combine(f.published_from, time())
        clauses.append(_meta("published_at") >= start.isoformat())
    if f.published_to:
        end = datetime.combine(f.published_to + timedelta(days=1), time())
        clauses.append(_meta("published_at") < end.isoformat())
    return clauses


def _config(name: str) -> Any:
    return literal_column(f"'{name}'::regconfig")


def _query(q: str) -> Any:
    english = func.websearch_to_tsquery(_config("english"), q)
    spanish = func.websearch_to_tsquery(_config("spanish"), q)
    return english.op("||")(spanish)


def _any_word(query: Any) -> Any:
    """The same lexemes joined by OR: a question rarely has all its words in the answer
    ("cómo conecto un agente" against a page without "cómo"). The lexemes are already
    stemmed, so the 'simple' configuration keeps them as they are."""
    joined = func.replace(cast(query, Text), " & ", " | ")
    return func.to_tsquery(_config("simple"), joined)


def _plain(q: str) -> bool:
    """No quotes or -exclusions, whose meaning OR would turn around."""
    return not re.search(r'"|(^|\s)-\S', q)


def _hit(chunk: FolioChunk, snippet: str) -> Hit:
    m = chunk.metadata_
    return Hit(
        node_id=chunk.node_id,
        title=m.get("title", ""),
        description=m.get("description", ""),
        heading_path=list(chunk.heading_path),
        anchor=chunk.anchor,
        url=m.get("url", ""),
        snippet=snippet,
        space=m.get("space", ""),
        doc_type=m.get("doc_type"),
        status=m.get("status", "published"),
    )


def _best_per_document(rows: list[tuple[FolioChunk, str, float]]) -> list[Hit]:
    """Rows come best first; keep each document's best chunk, in order."""
    seen: set[uuid.UUID] = set()
    hits = []
    for chunk, snippet, score in rows:
        if chunk.node_id in seen:
            continue
        seen.add(chunk.node_id)
        hit = _hit(chunk, snippet)
        hit.score = float(score)
        hits.append(hit)
    return hits


async def _text(db: AsyncSession, visible: ColumnElement[bool], q: str, f: Filters) -> list[Hit]:
    """Pages with every word; when none has them all, pages with any, those with more words
    first (cover density ranks them higher)."""
    hits = await _matching(db, visible, _query(q), f)
    if not hits and _plain(q):
        hits = await _matching(db, visible, _any_word(_query(q)), f)
    return hits


async def _matching(
    db: AsyncSession, visible: ColumnElement[bool], query: Any, f: Filters
) -> list[Hit]:
    rank = func.ts_rank_cd(FolioChunk.search_vector, query)
    # Cover density scores only the best cover, so the page's sections tie on its title;
    # counting every match breaks the tie in favor of the section that is about it.
    frequency = func.ts_rank(FolioChunk.search_vector, query)
    # Chunks are Markdown: its marks would clash with the ** around matches, and table
    # pipes, code ticks and rules read as noise in a snippet.
    readable = func.regexp_replace(FolioChunk.text, MARKUP, " ", "g")
    snippet = func.ts_headline(_config("spanish"), readable, query, SNIPPET)
    rows = await db.execute(
        select(FolioChunk, snippet, rank)
        .join(FolioNode, FolioNode.id == FolioChunk.node_id)
        .where(visible, FolioChunk.search_vector.op("@@")(query), *_where(f))
        .order_by(rank.desc(), frequency.desc(), FolioChunk.id)
        .limit(CANDIDATES)
    )
    return _best_per_document([(c, s, r) for c, s, r in rows.all()])


async def _semantic(
    db: AsyncSession, visible: ColumnElement[bool], q: str, f: Filters
) -> list[Hit] | None:
    """None when there is no provider to embed the question with."""
    cfg = await ai.load(db)
    if not cfg.enabled or not cfg.embedding_model:
        return None
    vector = (await ai.embed(cfg, q)).vector
    dims = len(vector)
    as_dims = Vector(dims)
    distance = cast(FolioChunk.embedding, as_dims).op("<=>", return_type=Float)(
        cast(vector, as_dims)
    )
    rows = await db.execute(
        select(FolioChunk, distance)
        .join(FolioNode, FolioNode.id == FolioChunk.node_id)
        .where(visible, FolioChunk.embedding_dims == dims, *_where(f))
        .order_by(distance, FolioChunk.id)
        .limit(SEMANTIC_TOP)
    )
    found = rows.all()
    return _best_per_document([(c, _lead(c.text), 1.0 - float(d)) for c, d in found])


def _lead(text: str, words: int = 30) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + (" …" if len(parts) > words else "")


def boosted(hits: list[Hit]) -> list[Hit]:
    for h in hits:
        h.score *= BOOST.get(h.status, 1.0)
    return sorted(hits, key=lambda h: h.score, reverse=True)


def fuse(lists: dict[str, list[Hit]]) -> list[Hit]:
    """Reciprocal Rank Fusion: each list adds 1 / (60 + rank) for the documents it found."""
    merged: dict[uuid.UUID, Hit] = {}
    for name, hits in lists.items():
        for rank, hit in enumerate(hits, start=1):
            target = merged.setdefault(hit.node_id, hit)
            if target is not hit:
                target.score += 1.0 / (RRF_K + rank)
            else:
                target.score = 1.0 / (RRF_K + rank)
            target.matched_by.append(name)
    return sorted(merged.values(), key=lambda h: h.score, reverse=True)


async def search(
    db: AsyncSession,
    user: User,
    q: str,
    *,
    mode: Mode = "hybrid",
    filters: Filters | None = None,
    limit: int = 10,
) -> list[Hit]:
    q = q.strip()
    if not q:
        raise ValidationFailed(
            "Write something to search for.", errors=[{"field": "q", "message": "empty"}]
        )
    f = filters or Filters()
    visible = await access.node_filter(db, user)
    if mode == "text":
        hits = await _text(db, visible, q, f)
        for h in hits:
            h.matched_by = ["text"]
        return boosted(hits)[:limit]
    try:
        semantic = await _semantic(db, visible, q, f)
    except ai.AiUnavailable:
        if mode == "semantic":
            raise
        semantic = None  # the provider is down: hybrid still answers with text
    if mode == "semantic":
        if semantic is None:
            raise ValidationFailed(
                "Semantic search needs an AI provider with an embedding model. An instance "
                "admin sets it in Admin, Settings, AI provider; meanwhile use mode=text.",
                code="no_embeddings",
                errors=[{"field": "mode", "message": "no provider"}],
            )
        for h in semantic:
            h.matched_by = ["semantic"]
        return boosted(semantic)[:limit]
    text_hits = await _text(db, visible, q, f)
    if semantic is None:
        for h in text_hits:
            h.matched_by = ["text"]
        return boosted(text_hits)[:limit]
    return boosted(fuse({"text": text_hits, "semantic": semantic}))[:limit]
