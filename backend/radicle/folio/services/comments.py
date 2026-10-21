"""Comments (Folio 2.3): threads at the foot of a page or anchored to its text, replies,
resolving, and orphans when the anchored text is deleted.

A thread is its first comment (`thread_id == id`); replies point at it. Bodies are written
in Markdown and stored as Folio JSON. Inline anchors follow the text (ADR 0040).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import CommentKind, FolioComment
from radicle.folio.db.models import FolioDraft, FolioNode, FolioSpace, FolioVersion
from radicle.folio.services import access, anchors, convert
from radicle.folio.services.parse_markdown import from_markdown
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.platform.services import events
from radicle.platform.services.markdown import extract_mentions

MAX_BODY = 10_000


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": message}])


def _body(markdown: str) -> dict[str, Any]:
    text = (markdown or "").strip()
    if not text:
        raise _invalid("body", "Write something in the comment.")
    if len(text) > MAX_BODY:
        raise _invalid("body", f"Comments have at most {MAX_BODY} characters.")
    return from_markdown(text)


def body_md(comment: FolioComment) -> str:
    return convert.to_markdown(comment.body_json).strip()


async def _space(db: AsyncSession, node: FolioNode) -> FolioSpace:
    space = await db.get(FolioSpace, node.space_id)
    if space is None:  # pragma: no cover - a node always has its space
        raise NotFound("Space not found.")
    return space


async def require_comment(db: AsyncSession, user: User, node: FolioNode) -> None:
    if "comment" not in await access.space_permissions(db, user, await _space(db, node)):
        raise Forbidden(
            f"You can't comment on '{node.title}': it takes the comment permission in its "
            "space. A space admin can give it.",
            code="comment_permission_denied",
        )


async def page_texts(db: AsyncSession, node: FolioNode) -> list[str]:
    """The page's plain text: its draft first, then what is published."""
    texts = []
    draft = await db.get(FolioDraft, node.id)
    if draft is not None:
        texts.append(convert.to_text(draft.content_json))
    if node.published_version_id is not None:
        version = await db.get(FolioVersion, node.published_version_id)
        if version is not None:
            texts.append(convert.to_text(version.content_json))
    return texts


async def _anchor(
    db: AsyncSession, node: FolioNode, anchor: dict[str, Any] | None, quote: str | None
) -> dict[str, Any]:
    """The anchor as found in the page now: the client's, or the first `quote`."""
    texts = await page_texts(db, node)
    for text in texts:
        if anchor is not None:
            found = anchors.relocate(text, anchors.Anchor.from_json(anchor))
        else:
            found = anchors.first(text, quote or "")
        if found is not None and found.quote.strip():
            return found.as_json()
    wanted = (anchor or {}).get("quote") or quote or ""
    raise _invalid("anchor", f"The text “{wanted[:80]}” is not in the page. Quote it exactly.")


async def get_comment(db: AsyncSession, user: User, comment_id: uuid.UUID) -> FolioComment:
    comment = await db.get(FolioComment, comment_id)
    if (
        comment is None
        or comment.deleted_at is not None
        or not await access.can_view(db, user, comment.node_id)
    ):
        raise NotFound(f"Comment {comment_id} not found.", code="comment_not_found")
    return comment


async def create(
    db: AsyncSession,
    user: User,
    node: FolioNode,
    *,
    body: str,
    inline: bool = False,
    anchor: dict[str, Any] | None = None,
    quote: str | None = None,
    thread_id: uuid.UUID | None = None,
) -> FolioComment:
    """A new thread (at the foot or anchored to `anchor` / the first `quote`), or a reply
    to `thread_id`."""
    await require_comment(db, user, node)
    content = _body(body)
    if thread_id is not None:
        root = await db.get(FolioComment, thread_id)
        if root is None or root.node_id != node.id or root.id != root.thread_id:
            raise _invalid("thread_id", f"Thread {thread_id} is not on this page.")
        if root.resolved_at is not None:
            raise Conflict("The thread is resolved. Reopen it to reply.", code="thread_resolved")
        comment = FolioComment(
            node_id=node.id, thread_id=root.id, parent_id=root.id, kind=root.kind
        )
    else:
        comment_id = uuid.uuid4()
        comment = FolioComment(
            id=comment_id,
            node_id=node.id,
            thread_id=comment_id,
            kind=CommentKind.inline if inline else CommentKind.footer,
        )
        if inline:
            if not anchor and not quote:
                raise _invalid("anchor", "An inline comment needs the text it is about.")
            comment.anchor = await _anchor(db, node, anchor, quote)
    comment.author_id = user.id
    comment.body_json = content
    comment.created_at = utcnow()
    db.add(comment)
    await db.flush()
    await _announce(db, user, comment)
    return comment


async def edit(db: AsyncSession, user: User, comment: FolioComment, body: str) -> FolioComment:
    if comment.author_id != user.id:
        raise Forbidden("You can only edit your own comments.", code="not_your_comment")
    comment.body_json = _body(body)
    comment.edited_at = utcnow()
    await db.flush()
    return comment


async def delete(db: AsyncSession, user: User, comment: FolioComment) -> None:
    """Your own, or any as an admin of the space. Deleting a thread's first comment hides
    the thread."""
    node = await db.get(FolioNode, comment.node_id)
    if comment.author_id != user.id:
        perms = await access.space_permissions(db, user, await _space(db, node)) if node else set()
        if "admin" not in perms:
            raise Forbidden(
                "You can only delete your own comments; space admins can delete any.",
                code="not_your_comment",
            )
    comment.deleted_at = utcnow()
    await db.flush()


async def _thread_root(db: AsyncSession, user: User, comment: FolioComment) -> FolioComment:
    root = await db.get(FolioComment, comment.thread_id)
    node = await db.get(FolioNode, comment.node_id)
    if root is None or node is None:  # pragma: no cover - a reply always has its thread
        raise NotFound("Thread not found.")
    await require_comment(db, user, node)
    return root


async def resolve(db: AsyncSession, user: User, comment: FolioComment) -> FolioComment:
    root = await _thread_root(db, user, comment)
    if root.resolved_at is None:
        root.resolved_at, root.resolved_by = utcnow(), user.id
        await db.flush()
    return root


async def reopen(db: AsyncSession, user: User, comment: FolioComment) -> FolioComment:
    root = await _thread_root(db, user, comment)
    root.resolved_at, root.resolved_by = None, None
    await db.flush()
    return root


@dataclass
class Thread:
    root: FolioComment
    replies: list[FolioComment] = field(default_factory=list)


async def threads(
    db: AsyncSession, user: User, node: FolioNode, *, include_resolved: bool = False
) -> list[Thread]:
    """The page's threads, oldest first, with their replies."""
    rows = await db.scalars(
        select(FolioComment)
        .where(FolioComment.node_id == node.id, FolioComment.deleted_at.is_(None))
        .order_by(FolioComment.created_at, FolioComment.id)
    )
    found: dict[uuid.UUID, Thread] = {}
    replies: list[FolioComment] = []
    for c in rows:
        if c.id == c.thread_id:
            if include_resolved or c.resolved_at is None:
                found[c.id] = Thread(c)
        else:
            replies.append(c)
    for r in replies:
        if r.thread_id in found:
            found[r.thread_id].replies.append(r)
    return list(found.values())


async def reanchor(db: AsyncSession, node: FolioNode, content: dict[str, Any]) -> None:
    """After the content changed: follow each inline anchor, or mark its thread orphaned
    (and back, if its text returns)."""
    rows = await db.scalars(
        select(FolioComment).where(
            FolioComment.node_id == node.id,
            FolioComment.kind == CommentKind.inline,
            FolioComment.id == FolioComment.thread_id,
            FolioComment.deleted_at.is_(None),
            FolioComment.anchor.is_not(None),
        )
    )
    text = convert.to_text(content)
    for comment in rows:
        moved = anchors.relocate(text, anchors.Anchor.from_json(comment.anchor or {}))
        if moved is None:
            comment.orphaned = True
        else:
            comment.orphaned = False
            comment.anchor = moved.as_json()
    await db.flush()


# --- notifications -------------------------------------------------------------------


async def _announce(db: AsyncSession, user: User, comment: FolioComment) -> None:
    payload = {"comment_id": str(comment.id), "node_id": str(comment.node_id)}
    mentioned = extract_mentions(body_md(comment))
    if mentioned:
        await events.emit(
            db, "folio", "comment_mention", actor=user, payload=payload | {"handles": mentioned}
        )
    await events.emit(db, "folio", "comment", actor=user, payload=payload | {"skip": mentioned})
