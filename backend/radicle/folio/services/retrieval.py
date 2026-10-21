"""The passages a chat answer is built from (Folio 4.5): phase 1's hybrid search, but over
sections instead of pages, so an answer can cite the exact one.

The reader's visibility goes into the SQL as in search: a restricted page never reaches the
model. Candidates from full text and from embeddings are fused with Reciprocal Rank Fusion,
then re-ranked: verified docs rise, outdated ones sink, a section whose heading names the
question's words rises, and no page takes more than three of the slots.
"""

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ColumnElement, Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioChunk, FolioNode
from radicle.folio.services import access, search
from radicle.platform.db.models import User
from radicle.platform.services import ai

TOP = 8
CANDIDATES = 30
PER_PAGE = 3
HEADING_BONUS = 0.25
STOPWORDS = frozenset(
    "a al como con cual cuando de del el en es la las lo los me mi para por que se sin su "
    "un una y o the an and are can do does for from how i in is it of on or to what when "
    "where which who why with my".split()
)


@dataclass
class Passage:
    chunk_id: int
    node_id: uuid.UUID
    version: int | None
    anchor: str | None
    title: str
    section: str
    url: str
    text: str
    space: str
    status: str
    owner: str | None
    score: float = 0.0
    matched_by: list[str] = field(default_factory=list)

    @property
    def outdated(self) -> bool:
        return self.status == "outdated"


def _passage(chunk: FolioChunk) -> Passage:
    m: dict[str, Any] = chunk.metadata_
    return Passage(
        chunk_id=chunk.id,
        node_id=chunk.node_id,
        version=m.get("version"),
        anchor=chunk.anchor,
        title=m.get("title", ""),
        section=m.get("section", ""),
        url=m.get("url", ""),
        text=chunk.text,
        space=m.get("space", ""),
        status=m.get("status", "published"),
        owner=m.get("owner"),
    )


async def _text(
    db: AsyncSession, visible: ColumnElement[bool], q: str, f: search.Filters
) -> list[Passage]:
    found = await _matching(db, visible, search._query(q), f)
    if not found and search._plain(q):
        found = await _matching(db, visible, search._any_word(search._query(q)), f)
    return found


async def _matching(
    db: AsyncSession, visible: ColumnElement[bool], query: Any, f: search.Filters
) -> list[Passage]:
    rank = func.ts_rank_cd(FolioChunk.search_vector, query)
    frequency = func.ts_rank(FolioChunk.search_vector, query)
    rows = await db.scalars(
        select(FolioChunk)
        .join(FolioNode, FolioNode.id == FolioChunk.node_id)
        .where(visible, FolioChunk.search_vector.op("@@")(query), *search._where(f))
        .order_by(rank.desc(), frequency.desc(), FolioChunk.id)
        .limit(CANDIDATES)
    )
    return [_passage(c) for c in rows]


async def _semantic(
    db: AsyncSession, visible: ColumnElement[bool], q: str, f: search.Filters
) -> list[Passage]:
    cfg = await ai.load(db)
    if not cfg.enabled or not cfg.embedding_model:
        return []
    try:
        vector = (await ai.embed(cfg, q)).vector
    except ai.AiUnavailable:
        return []  # embeddings are down: full text still answers
    as_dims = Vector(len(vector))
    distance = cast(FolioChunk.embedding, as_dims).op("<=>", return_type=Float)(
        cast(vector, as_dims)
    )
    rows = await db.scalars(
        select(FolioChunk)
        .join(FolioNode, FolioNode.id == FolioChunk.node_id)
        .where(visible, FolioChunk.embedding_dims == len(vector), *search._where(f))
        .order_by(distance, FolioChunk.id)
        .limit(CANDIDATES)
    )
    return [_passage(c) for c in rows]


def _words(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch))
    return {w for w in re.findall(r"[a-z0-9]{3,}", plain) if w not in STOPWORDS}


def _stem(word: str) -> str:
    return word[:5]


def rerank(question: str, passages: list[Passage], top: int = TOP) -> list[Passage]:
    """Status boost and heading match on the fused score, then at most three per page."""
    asked = {_stem(w) for w in _words(question)}
    for p in passages:
        p.score *= search.BOOST.get(p.status, 1.0)
        heading = {_stem(w) for w in _words(f"{p.title} {p.section}")}
        if asked:
            p.score *= 1 + HEADING_BONUS * len(asked & heading) / len(asked)
    ranked = sorted(passages, key=lambda p: (-p.score, p.chunk_id))
    per_page: dict[uuid.UUID, int] = {}
    kept = []
    for p in ranked:
        if per_page.get(p.node_id, 0) >= PER_PAGE:
            continue
        per_page[p.node_id] = per_page.get(p.node_id, 0) + 1
        kept.append(p)
        if len(kept) == top:
            break
    return kept


def fuse(lists: dict[str, list[Passage]]) -> list[Passage]:
    merged: dict[int, Passage] = {}
    for name, found in lists.items():
        for rank, p in enumerate(found, start=1):
            target = merged.setdefault(p.chunk_id, p)
            target.score += 1.0 / (search.RRF_K + rank)
            target.matched_by.append(name)
    return list(merged.values())


async def retrieve(
    db: AsyncSession,
    user: User,
    question: str,
    *,
    filters: search.Filters | None = None,
    top: int = TOP,
) -> list[Passage]:
    """The best sections for the question among those the user may read."""
    q = question.strip()
    if not q:
        return []
    f = filters or search.Filters()
    visible = await access.node_filter(db, user)
    found = {"text": await _text(db, visible, q, f), "semantic": await _semantic(db, visible, q, f)}
    return rerank(q, fuse(found), top)
