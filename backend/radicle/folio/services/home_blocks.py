"""The home's blocks resolved for whoever looks (Folio 3.2): the active layout, block by
block, with the viewer's permissions. A block that ends up with nothing to show is left
out, so nobody sees an empty card or learns that something hidden exists.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace, NodeKind
from radicle.folio.services import access, chat, doc_query, feed, home_layouts, spaces, views
from radicle.folio.services.home import (
    ANNOUNCEMENT_LABELS,
    FEATURED_LABELS,
    Card,
    Rows,
    SpaceCount,
    _cards,
    _labelled,
    _published,
)
from radicle.platform.db.models import User
from radicle.platform.query.errors import RQLError


@dataclass
class Block:
    id: str
    type: str
    x: int
    y: int
    w: int
    h: int
    title: str = ""
    cards: list[Card] = field(default_factory=list)
    spaces: list[SpaceCount] = field(default_factory=list)
    markdown: str = ""
    # chat: whether the docs chat is on (Folio 4.5)
    live: bool = False

    @property
    def empty(self) -> bool:
        if self.type == "search":
            return False
        if self.type == "chat":
            return not self.live
        return not (self.cards or self.spaces or self.markdown.strip())


async def _fixed_or_newest(
    db: AsyncSession, base: Rows, config: dict[str, Any], labels: tuple[str, ...], posts_first: bool
) -> list[Card]:
    if config.get("node"):
        # A fixed page the viewer can't see leaves the block empty, never a fallback.
        return await _cards(db, base.where(FolioNode.id == uuid.UUID(config["node"])), 1)
    posts = base.where(FolioNode.kind == NodeKind.blog_post)
    found = await _cards(db, base.where(_labelled(labels)), 1)
    if not found and posts_first:
        found = await _cards(db, posts, 1) or await _cards(db, base, 1)
    return found


async def _most_read(db: AsyncSession, base: Rows, limit: int) -> list[Card]:
    read = views.most_read_since(7)
    by_reads = (
        base.join(read, read.c.node_id == FolioNode.id)
        .order_by(None)
        .order_by(read.c.views.desc(), FolioNode.published_at.desc(), FolioNode.id)
    )
    out = await _cards(db, by_reads, limit)
    if len(out) < limit:
        seen = [c.id for c in out]
        more = base.where(FolioNode.id.not_in(seen)) if seen else base
        out += await _cards(db, more, limit - len(out))
    return out


async def _query(db: AsyncSession, user: User, base: Rows, rql: str, limit: int) -> list[Card]:
    try:
        found = await doc_query.query(db, user, rql, limit=limit)
    except RQLError:
        return []  # a layout saved before a field changed: hide the block
    ids = [d.node.id for d in found.items]
    if not ids:
        return []
    cards = {c.id: c for c in await _cards(db, base.where(FolioNode.id.in_(ids)), limit)}
    return [cards[i] for i in ids if i in cards]


async def _spaces(db: AsyncSession, user: User, visible: ColumnElement[bool]) -> list[SpaceCount]:
    counted = await db.execute(
        select(FolioNode.space_id, func.count())
        .where(
            visible,
            FolioNode.kind != NodeKind.folder,
            FolioNode.published_version_id.is_not(None),
            FolioNode.archived_at.is_(None),
        )
        .group_by(FolioNode.space_id)
    )
    counts: dict[uuid.UUID, int] = {space_id: int(n) for space_id, n in counted.all()}
    return [
        SpaceCount(s.key, s.name, s.kind.value, s.icon, counts.get(s.id, 0))
        for s in await spaces.list_spaces(db, user)
    ]


async def resolve(
    db: AsyncSession, user: User, layout: dict[str, Any] | None = None
) -> list[Block]:
    """The layout's blocks with their content for `user`, empty ones left out."""
    layout = layout or await home_layouts.active(db)
    visible = await access.node_filter(db, user)
    base = _published(visible)
    chat_on: bool | None = None
    out: list[Block] = []
    for raw in layout.get("blocks", []):
        config: dict[str, Any] = raw.get("config", {})
        block = Block(
            id=raw["id"],
            type=raw["type"],
            x=raw["x"],
            y=raw["y"],
            w=raw["w"],
            h=raw["h"],
            title=str(config.get("title", "")),
        )
        kind = block.type
        if kind == "featured":
            block.cards = await _fixed_or_newest(db, base, config, FEATURED_LABELS, True)
        elif kind == "announcement":
            block.cards = await _fixed_or_newest(db, base, config, ANNOUNCEMENT_LABELS, False)
        elif kind == "posts":
            query = base
            if config.get("kind", "posts") == "posts":
                query = query.where(FolioNode.kind == NodeKind.blog_post)
            if config.get("space"):
                query = query.where(FolioSpace.key == config["space"])
            if config.get("label"):
                query = query.where(_labelled((config["label"],)))
            block.cards = await _cards(db, query, int(config.get("limit", 6)))
        elif kind == "query":
            block.cards = await _query(
                db, user, base, config.get("rql", ""), int(config.get("limit", 6))
            )
        elif kind == "for_you":
            block.cards = [i.card for i in await feed.feed(db, user, int(config.get("limit", 5)))]
        elif kind == "most_read":
            block.cards = await _most_read(db, base, int(config.get("limit", 5)))
        elif kind == "spaces":
            block.spaces = await _spaces(db, user, visible)
        elif kind == "text":
            block.markdown = str(config.get("markdown", ""))
        elif kind == "chat":
            if chat_on is None:
                chat_on = await chat.unavailable(db) is None
            block.live = chat_on
        # search shows the box; chat shows only when the docs chat is on.
        if not block.empty:
            out.append(block)
    return out
