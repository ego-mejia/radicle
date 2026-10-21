"""Folio's home (Folio 1.8): the default bento resolved for the caller.

Blocks: a featured doc, the latest announcement, AI Tools, the latest posts, the spaces
with how many docs each has, and the most read in the last seven days (topped up with the
latest published while there are few reads).
Every block reads only published docs the caller may see, through the visibility rule.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioRole, FolioSpace, FolioVersion, NodeKind
from radicle.folio.services import access, roles, spaces, views
from radicle.platform.db.models import User

FEATURED_LABELS = ("featured", "destacado")
ANNOUNCEMENT_LABELS = ("anuncio", "announcement")
AI_TOOLS_SPACE = "ai-tools"
Rows = Select[FolioNode, FolioSpace, FolioVersion, User]
WORDS_PER_MINUTE = 200


@dataclass(frozen=True)
class Card:
    id: uuid.UUID
    kind: str
    title: str
    slug: str
    icon: str | None
    cover_asset_id: uuid.UUID | None
    space: str
    space_name: str
    description: str
    doc_type: str | None
    labels: list[str]
    author: str | None
    author_name: str | None
    published_at: datetime | None
    reading_minutes: int
    status: str


@dataclass(frozen=True)
class SpaceCount:
    key: str
    name: str
    kind: str
    icon: str | None
    docs: int


@dataclass
class Home:
    can_write: bool
    featured: Card | None = None
    announcement: Card | None = None
    ai_tools: list[Card] = field(default_factory=list)
    latest_posts: list[Card] = field(default_factory=list)
    spaces: list[SpaceCount] = field(default_factory=list)
    most_read: list[Card] = field(default_factory=list)


def _published(visible: ColumnElement[bool]) -> Rows:
    return (
        select(FolioNode, FolioSpace, FolioVersion, User)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .join(FolioVersion, FolioVersion.id == FolioNode.published_version_id)
        .outerjoin(User, User.id == FolioVersion.author_id)
        .where(visible, FolioNode.kind != NodeKind.folder, FolioNode.archived_at.is_(None))
        .order_by(FolioNode.published_at.desc(), FolioNode.id)
    )


def _card(node: FolioNode, space: FolioSpace, version: FolioVersion, author: User | None) -> Card:
    meta = version.metadata_
    words = len(version.content_text.split())
    return Card(
        id=node.id,
        kind=node.kind.value,
        title=version.title,
        slug=node.slug,
        icon=node.icon,
        cover_asset_id=node.cover_asset_id,
        space=space.key,
        space_name=space.name,
        description=str(meta.get("description", "")),
        doc_type=meta.get("doc_type"),
        labels=list(meta.get("labels", [])),
        author=author.handle if author else None,
        author_name=author.display_name if author else None,
        published_at=node.published_at,
        reading_minutes=max(1, round(words / WORDS_PER_MINUTE)),
        status=node.status.value,
    )


async def _cards(db: AsyncSession, query: Rows, limit: int) -> list[Card]:
    rows = await db.execute(query.limit(limit))
    return [_card(n, s, v, a) for n, s, v, a in rows.all()]


def _labelled(labels: tuple[str, ...]) -> ColumnElement[bool]:
    labelled = FolioVersion.metadata_["labels"]
    return or_(*(labelled.contains([label]) for label in labels))


async def home(db: AsyncSession, user: User) -> Home:
    visible = await access.node_filter(db, user)
    role = await roles.effective_role(db, user)
    base = _published(visible)
    posts = base.where(FolioNode.kind == NodeKind.blog_post)
    out = Home(can_write=role in (FolioRole.creator, FolioRole.admin))

    featured = (
        await _cards(db, base.where(_labelled(FEATURED_LABELS)), 1)
        or await _cards(db, posts, 1)
        or await _cards(db, base, 1)
    )
    out.featured = featured[0] if featured else None
    announcement = await _cards(db, posts.where(_labelled(ANNOUNCEMENT_LABELS)), 1)
    out.announcement = announcement[0] if announcement else None
    out.ai_tools = await _cards(db, base.where(FolioSpace.key == AI_TOOLS_SPACE), 3)
    out.latest_posts = await _cards(db, posts, 6)
    read = views.most_read_since(7)
    by_reads = (
        base.join(read, read.c.node_id == FolioNode.id)
        .order_by(None)
        .order_by(read.c.views.desc(), FolioNode.published_at.desc(), FolioNode.id)
    )
    out.most_read = await _cards(db, by_reads, 5)
    if len(out.most_read) < 5:
        seen = [c.id for c in out.most_read]
        more = base.where(FolioNode.id.not_in(seen)) if seen else base
        out.most_read += await _cards(db, more, 5 - len(out.most_read))

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
    out.spaces = [
        SpaceCount(s.key, s.name, s.kind.value, s.icon, counts.get(s.id, 0))
        for s in await spaces.list_spaces(db, user)
    ]
    return out
