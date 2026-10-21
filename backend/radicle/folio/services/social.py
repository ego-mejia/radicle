"""Following, favorites, reactions and reading history (Folio 2.4, 2.7).

Targets are a node or a space (reactions: a node or a comment). Everything checks that
you can see the target, and lists only show what you can still see.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import (
    FolioComment,
    FolioFavorite,
    FolioReaction,
    FolioView,
    FolioWatch,
    TargetType,
    WatchSource,
)
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import access
from radicle.platform.db.models import User, UserKind, utcnow
from radicle.platform.errors import NotFound, ValidationFailed

REACTIONS = ("👍", "❤️", "🎉", "👀", "🚀", "✅")
VIEW_DEDUP = timedelta(minutes=30)


async def target(db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID) -> None:
    """404 unless you can see the node, space or comment."""
    if kind == TargetType.node:
        ok = await access.can_view(db, user, target_id)
    elif kind == TargetType.space:
        ok = target_id in await access.visible_space_ids(db, user)
    else:
        comment = await db.get(FolioComment, target_id)
        ok = bool(comment and not comment.deleted_at) and await access.can_view(
            db, user, comment.node_id if comment else target_id
        )
    if not ok:
        raise NotFound(f"{kind.value.capitalize()} {target_id} not found.", code="not_found")


def _watchable(kind: TargetType) -> None:
    if kind == TargetType.comment:
        raise ValidationFailed(
            "You can follow a page or a space, not a comment.",
            errors=[{"field": "target_type", "message": "node or space"}],
        )


async def watch(
    db: AsyncSession,
    user: User,
    kind: TargetType,
    target_id: uuid.UUID,
    *,
    source: WatchSource = WatchSource.manual,
) -> None:
    _watchable(kind)
    await target(db, user, kind, target_id)
    await db.execute(
        insert(FolioWatch)
        .values(user_id=user.id, target_type=kind, target_id=target_id, source=source)
        .on_conflict_do_nothing()
    )


async def unwatch(db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID) -> None:
    _watchable(kind)
    await db.execute(
        delete(FolioWatch).where(
            FolioWatch.user_id == user.id,
            FolioWatch.target_type == kind,
            FolioWatch.target_id == target_id,
        )
    )


async def watchers(db: AsyncSession, node: FolioNode, *, with_space: bool) -> set[uuid.UUID]:
    """Who follows the page (and, with `with_space`, its space)."""
    query = select(FolioWatch.user_id).where(
        (FolioWatch.target_type == TargetType.node) & (FolioWatch.target_id == node.id)
    )
    if with_space:
        query = select(FolioWatch.user_id).where(
            ((FolioWatch.target_type == TargetType.node) & (FolioWatch.target_id == node.id))
            | (
                (FolioWatch.target_type == TargetType.space)
                & (FolioWatch.target_id == node.space_id)
            )
        )
    return set(await db.scalars(query))


async def is_watching(db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(FolioWatch.user_id).where(
            FolioWatch.user_id == user.id,
            FolioWatch.target_type == kind,
            FolioWatch.target_id == target_id,
        )
    )
    return found is not None


async def favorite(db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID) -> None:
    _watchable(kind)
    await target(db, user, kind, target_id)
    await db.execute(
        insert(FolioFavorite)
        .values(user_id=user.id, target_type=kind, target_id=target_id)
        .on_conflict_do_nothing()
    )


async def unfavorite(db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID) -> None:
    await db.execute(
        delete(FolioFavorite).where(
            FolioFavorite.user_id == user.id,
            FolioFavorite.target_type == kind,
            FolioFavorite.target_id == target_id,
        )
    )


def _emoji(emoji: str) -> str:
    if emoji not in REACTIONS:
        raise ValidationFailed(
            f"Pick one of {' '.join(REACTIONS)}.",
            errors=[{"field": "emoji", "message": "not a reaction"}],
        )
    return emoji


async def react(
    db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID, emoji: str
) -> None:
    if kind == TargetType.space:
        raise ValidationFailed(
            "React to a page or a comment.",
            errors=[{"field": "target_type", "message": "node or comment"}],
        )
    await target(db, user, kind, target_id)
    await db.execute(
        insert(FolioReaction)
        .values(target_type=kind, target_id=target_id, user_id=user.id, emoji=_emoji(emoji))
        .on_conflict_do_nothing()
    )


async def unreact(
    db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID, emoji: str
) -> None:
    await db.execute(
        delete(FolioReaction).where(
            FolioReaction.target_type == kind,
            FolioReaction.target_id == target_id,
            FolioReaction.user_id == user.id,
            FolioReaction.emoji == emoji,
        )
    )


@dataclass(frozen=True)
class Reaction:
    emoji: str
    count: int
    mine: bool


async def reactions(
    db: AsyncSession, user: User, kind: TargetType, target_id: uuid.UUID
) -> list[Reaction]:
    rows = await db.execute(
        select(
            FolioReaction.emoji,
            func.count(),
            func.bool_or(FolioReaction.user_id == user.id),
        )
        .where(FolioReaction.target_type == kind, FolioReaction.target_id == target_id)
        .group_by(FolioReaction.emoji)
    )
    found = {e: Reaction(e, int(n), bool(m)) for e, n, m in rows.all()}
    return [found[e] for e in REACTIONS if e in found]


async def record_view(db: AsyncSession, user: User, node: FolioNode) -> None:
    """A person read the page. Reads within 30 minutes count once, but move the page to
    the top of their recents."""
    if user.kind != UserKind.human:
        return
    recent = await db.scalar(
        select(FolioView).where(
            FolioView.node_id == node.id,
            FolioView.user_id == user.id,
            FolioView.viewed_at > utcnow() - VIEW_DEDUP,
        )
    )
    if recent is None:
        db.add(FolioView(node_id=node.id, user_id=user.id, viewed_at=utcnow()))
    else:
        recent.viewed_at = utcnow()
    await db.flush()


async def recents(db: AsyncSession, user: User, limit: int = 10) -> list[FolioNode]:
    """What you read last, newest first, once each."""
    last = (
        select(FolioView.node_id, func.max(FolioView.viewed_at).label("at"))
        .where(FolioView.user_id == user.id)
        .group_by(FolioView.node_id)
        .subquery()
    )
    rows = await db.scalars(
        select(FolioNode)
        .join(last, last.c.node_id == FolioNode.id)
        .where(await access.node_filter(db, user), FolioNode.archived_at.is_(None))
        .order_by(last.c.at.desc())
        .limit(limit)
    )
    return list(rows)


async def favorites(db: AsyncSession, user: User) -> tuple[list[FolioNode], list[FolioSpace]]:
    """Your starred pages and spaces you can still see, newest first."""
    nodes = await db.scalars(
        select(FolioNode)
        .join(
            FolioFavorite,
            (FolioFavorite.target_id == FolioNode.id)
            & (FolioFavorite.target_type == TargetType.node)
            & (FolioFavorite.user_id == user.id),
        )
        .where(await access.node_filter(db, user), FolioNode.archived_at.is_(None))
        .order_by(FolioFavorite.created_at.desc())
    )
    space_ids = await access.visible_space_ids(db, user)
    spaces = await db.scalars(
        select(FolioSpace)
        .join(
            FolioFavorite,
            (FolioFavorite.target_id == FolioSpace.id)
            & (FolioFavorite.target_type == TargetType.space)
            & (FolioFavorite.user_id == user.id),
        )
        .where(FolioSpace.id.in_(space_ids))
        .order_by(FolioFavorite.created_at.desc())
    )
    return list(nodes), list(spaces)
