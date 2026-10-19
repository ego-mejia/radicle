"""Comments with markdown, @mentions and emoji reactions."""

import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.core.permissions import can_see
from radicle.db.models import (
    Comment,
    CommentReaction,
    EventType,
    Project,
    Ticket,
    User,
    utcnow,
)
from radicle.services import history
from radicle.services.access import ProjectAccess, access_for
from radicle.services.tickets import bump, sync_mentions

BODY_MAX = 50_000
EMOJI_MAX_CODEPOINTS = 16


def check_body(body: str) -> str:
    if not body.strip():
        raise ValidationFailed(
            "Comment cannot be empty.", errors=[{"field": "body_md", "message": "empty"}]
        )
    if len(body) > BODY_MAX:
        raise ValidationFailed(
            f"Comment must be at most {BODY_MAX} characters.",
            errors=[{"field": "body_md", "message": "too long"}],
        )
    return body


def check_emoji(emoji: str) -> str:
    """One emoji, possibly with modifiers or ZWJ sequences; no letters, digits or spaces."""
    value = emoji.strip()
    allowed = {"So", "Sk", "Mn", "Me", "Cf"}
    if (
        not value
        or len(value) > EMOJI_MAX_CODEPOINTS
        or any(unicodedata.category(ch) not in allowed for ch in value)
        or not any(unicodedata.category(ch) == "So" for ch in value)
    ):
        raise ValidationFailed(
            f"'{emoji}' is not a single emoji. Send one Unicode emoji, e.g. 👍.",
            errors=[{"field": "emoji", "message": "invalid"}],
        )
    return value


@dataclass
class ReactionSummary:
    emoji: str
    count: int
    users: list[str] = field(default_factory=list)


async def add_comment(
    db: AsyncSession, access: ProjectAccess, ticket: Ticket, body: str
) -> Comment:
    comment = Comment(
        id=uuid.uuid4(), ticket_id=ticket.id, author_id=access.user.id, body_md=check_body(body)
    )
    db.add(comment)
    await db.flush()
    await sync_mentions(db, ticket.id, comment.id, comment.body_md)
    history.record(
        db, ticket, access.user, EventType.comment_added, new={"comment_id": str(comment.id)}
    )
    bump(ticket)
    await db.flush()
    await db.refresh(comment, ["author"])
    return comment


async def list_comments(
    db: AsyncSession,
    ticket: Ticket,
    *,
    limit: int,
    newest_first: bool,
    after: tuple[datetime, str] | None,
) -> list[Comment]:
    query = select(Comment).where(Comment.ticket_id == ticket.id)
    key = tuple_(Comment.created_at, Comment.id)
    if after is not None:
        query = query.where(key < after if newest_first else key > after)
    order = (
        (Comment.created_at.desc(), Comment.id.desc())
        if newest_first
        else (Comment.created_at, Comment.id)
    )
    return list(await db.scalars(query.order_by(*order).limit(limit)))


async def reactions_for(
    db: AsyncSession, comment_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[ReactionSummary]]:
    if not comment_ids:
        return {}
    rows = await db.scalars(
        select(CommentReaction)
        .where(CommentReaction.comment_id.in_(comment_ids))
        .order_by(CommentReaction.created_at)
    )
    result: dict[uuid.UUID, dict[str, ReactionSummary]] = {}
    for row in rows:
        by_emoji = result.setdefault(row.comment_id, {})
        summary = by_emoji.setdefault(row.emoji, ReactionSummary(row.emoji, 0))
        summary.count += 1
        summary.users.append(row.user.handle)
    return {cid: list(by_emoji.values()) for cid, by_emoji in result.items()}


@dataclass(frozen=True)
class CommentAccess:
    comment: Comment
    ticket: Ticket
    access: ProjectAccess


async def load_comment(
    db: AsyncSession,
    user: User,
    comment_id: uuid.UUID,
    *,
    permission: str | None = None,
    write: bool = False,
) -> CommentAccess:
    not_found = NotFound(f"Comment {comment_id} not found.", code="comment_not_found")
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise not_found
    ticket = await db.scalar(
        select(Ticket).where(Ticket.id == comment.ticket_id).with_for_update(of=Ticket)
    )
    if ticket is None or ticket.deleted_at is not None:
        raise not_found
    project = await db.get(Project, ticket.project_id)
    if project is None:  # pragma: no cover - FK
        raise not_found
    try:
        access = await access_for(
            db, user, project, write=write or permission is not None, permission=permission
        )
    except NotFound:
        raise not_found from None
    if not await can_see(db, user, ticket):
        raise not_found
    return CommentAccess(comment, ticket, access)


async def edit_comment(db: AsyncSession, ca: CommentAccess, body: str) -> Comment:
    if ca.comment.author_id != ca.access.user.id:
        raise Forbidden("Only the author can edit a comment.", code="not_author")
    body = check_body(body)
    if body != ca.comment.body_md:
        ca.comment.body_md = body
        ca.comment.edited_at = utcnow()
        await sync_mentions(db, ca.ticket.id, ca.comment.id, body)
        history.record(
            db,
            ca.ticket,
            ca.access.user,
            EventType.comment_edited,
            new={"comment_id": str(ca.comment.id)},
        )
        bump(ca.ticket)
        await db.flush()
    return ca.comment


async def delete_comment(db: AsyncSession, ca: CommentAccess) -> None:
    is_author = ca.comment.author_id == ca.access.user.id
    ca.access.require("comment.create" if is_author else "comment.delete_any")
    ca.comment.deleted_at = utcnow()
    await sync_mentions(db, ca.ticket.id, ca.comment.id, "")
    history.record(
        db,
        ca.ticket,
        ca.access.user,
        EventType.comment_deleted,
        old={"comment_id": str(ca.comment.id)},
    )
    bump(ca.ticket)
    await db.flush()


async def set_reaction(db: AsyncSession, ca: CommentAccess, emoji: str, on: bool) -> None:
    emoji = check_emoji(emoji)
    key = (ca.comment.id, ca.access.user.id, emoji)
    existing = await db.get(CommentReaction, key)
    if on and existing is None:
        db.add(CommentReaction(comment_id=key[0], user_id=key[1], emoji=emoji))
    elif not on:
        if existing is None:
            raise Conflict(f"You have not reacted with {emoji}.", code="no_reaction")
        await db.delete(existing)
    await db.flush()
