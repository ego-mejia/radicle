"""Who hears about comments (Folio 2.3): a comment or reply reaches the page's watchers and
the thread's participants; a mention reaches the person mentioned at once. Nobody hears
about a page they can't see (the bus already skips the actor)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioComment
from radicle.folio.db.models import FolioNode
from radicle.folio.services import access, convert, social
from radicle.platform.db.models import OutboxEvent, User
from radicle.platform.services import events

SNIPPET = 280


async def _context(
    db: AsyncSession, event: OutboxEvent
) -> tuple[FolioComment, FolioNode, str] | None:
    comment = await db.get(FolioComment, uuid.UUID(event.payload["comment_id"]))
    node = await db.get(FolioNode, uuid.UUID(event.payload["node_id"]))
    if comment is None or node is None or comment.deleted_at is not None:
        return None
    actor = await db.get(User, event.actor_id) if event.actor_id else None
    return comment, node, f"@{actor.handle}" if actor else "Someone"


def _notice(
    user_id: uuid.UUID, reason: str, title: str, comment: FolioComment, node: FolioNode
) -> events.Notice:
    text = convert.to_text(comment.body_json)
    body = text if len(text) <= SNIPPET else text[: SNIPPET - 1] + "…"
    link = f"/folio/p/{node.id}-{node.slug}#comment-{comment.thread_id}"
    return events.Notice(user_id, reason, title, body, link)


async def _visible(db: AsyncSession, node: FolioNode, ids: set[uuid.UUID]) -> list[User]:
    users = await db.scalars(select(User).where(User.id.in_(ids)))
    return [u for u in users if await access.can_view(db, u, node.id)]


@events.resolver("folio", "comment", label="Comments on pages you follow or threads you're in")
async def _comment(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    found = await _context(db, event)
    if found is None:
        return []
    comment, node, actor = found
    participants = set(
        await db.scalars(
            select(FolioComment.author_id).where(
                FolioComment.thread_id == comment.thread_id,
                FolioComment.deleted_at.is_(None),
                FolioComment.author_id.is_not(None),
            )
        )
    )
    ids = {i for i in participants if i is not None} | await social.watchers(
        db, node, with_space=False
    )
    skip = {h.lower() for h in event.payload.get("skip", [])}
    reply = comment.id != comment.thread_id
    verb = "replied in a thread on" if reply else "commented on"
    return [
        _notice(
            u.id,
            "participant" if u.id in participants else "watcher",
            f"{actor} {verb} '{node.title}'",
            comment,
            node,
        )
        for u in await _visible(db, node, ids)
        if u.handle.lower() not in skip
    ]


@events.resolver("folio", "comment_mention", label="Mentions in comments")
async def _mention(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    found = await _context(db, event)
    if found is None:
        return []
    comment, node, actor = found
    handles = [h.lower() for h in event.payload.get("handles", [])]
    ids = set(await db.scalars(select(User.id).where(User.handle.in_(handles))))
    return [
        _notice(u.id, "mention", f"{actor} mentioned you on '{node.title}'", comment, node)
        for u in await _visible(db, node, ids)
    ]
