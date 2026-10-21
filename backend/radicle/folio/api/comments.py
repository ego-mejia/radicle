"""Comments over REST (Folio 2.3): threads at the foot of a page or anchored to its text."""

import uuid
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import ConfigDict, Field

from radicle.folio.db.collab import FolioComment
from radicle.folio.services import comments, nodes
from radicle.folio.services.comments import Thread
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound

router = APIRouter(tags=["folio"])


class FolioAnchor(Output):
    quote: str = Field(description="The anchored text as it reads now")
    prefix: str = Field(description="Up to 32 characters before it in the page's text")
    suffix: str = Field(description="Up to 32 characters after it")
    offset: int = Field(description="Where it starts in the page's plain text")


class FolioAnchorIn(Input):
    # The context's spaces are part of where the quote sits: keep them.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    quote: str = Field(min_length=1, max_length=1000)
    prefix: str = Field(default="", max_length=64)
    suffix: str = Field(default="", max_length=64)
    offset: int = Field(default=0, ge=0)


class FolioCommentOut(Output):
    id: uuid.UUID
    thread_id: uuid.UUID
    author: str | None = Field(description="Handle; null when the person was removed")
    author_name: str | None
    body_md: str
    created_at: UtcDatetime
    edited_at: UtcDatetime | None
    mine: bool


class FolioThreadOut(Output):
    id: uuid.UUID = Field(description="The thread's first comment")
    kind: Literal["footer", "inline"]
    anchor: FolioAnchor | None
    orphaned: bool = Field(description="Its anchored text was deleted; shown with its quote")
    resolved_at: UtcDatetime | None
    resolved_by: str | None
    comments: list[FolioCommentOut]


class FolioCommentIn(Input):
    body: str = Field(description="Markdown; @handle mentions notify")
    inline: bool = False
    anchor: FolioAnchorIn | None = Field(default=None, description="For an inline thread")
    quote: str | None = Field(
        default=None, description="Instead of anchor: inline on the first occurrence"
    )
    thread_id: uuid.UUID | None = Field(default=None, description="Reply to this thread")


class FolioCommentPatch(Input):
    body: str


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


async def _people(db: Db, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, User]:
    found = {}
    for i in ids:
        if i is not None:
            user = await db.get(User, i)
            if user is not None:
                found[i] = user
    return found


def _comment(c: FolioComment, people: dict[uuid.UUID, User], me: User) -> FolioCommentOut:
    author = people.get(c.author_id) if c.author_id else None
    return FolioCommentOut(
        id=c.id,
        thread_id=c.thread_id,
        author=author.handle if author else None,
        author_name=author.display_name if author else None,
        body_md=comments.body_md(c),
        created_at=c.created_at,
        edited_at=c.edited_at,
        mine=c.author_id == me.id,
    )


async def _thread(db: Db, thread: Thread, me: User) -> FolioThreadOut:
    root = thread.root
    everyone = [root, *thread.replies]
    people = await _people(db, {c.author_id for c in everyone} | {root.resolved_by})
    resolver = people.get(root.resolved_by) if root.resolved_by else None
    anchor = root.anchor
    return FolioThreadOut(
        id=root.id,
        kind=root.kind.value,
        anchor=FolioAnchor(
            quote=anchor["quote"],
            prefix=anchor.get("prefix", ""),
            suffix=anchor.get("suffix", ""),
            offset=anchor.get("offset", 0),
        )
        if anchor
        else None,
        orphaned=root.orphaned,
        resolved_at=root.resolved_at,
        resolved_by=resolver.handle if resolver else None,
        comments=[_comment(c, people, me) for c in everyone],
    )


async def _whole(db: Db, me: User, comment: FolioComment) -> FolioThreadOut:
    node = await nodes.get_node(db, me, comment.node_id)
    found = await comments.threads(db, me, node, include_resolved=True)
    thread = next((t for t in found if t.root.id == comment.thread_id), None)
    if thread is None:
        raise NotFound("The thread was deleted.", code="thread_deleted")
    return await _thread(db, thread, me)


@router.get("/nodes/{node_id}/comments", response_model=Page[FolioThreadOut])
async def list_comments(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db, include_resolved: bool = False
) -> Page[FolioThreadOut]:
    """The page's threads, oldest first, with their replies. Orphaned inline threads keep
    their quote."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    found = await comments.threads(db, principal.user, node, include_resolved=include_resolved)
    return Page(items=[await _thread(db, t, principal.user) for t in found])


@router.post("/nodes/{node_id}/comments", response_model=FolioThreadOut, status_code=201)
async def add_comment(
    node_id: uuid.UUID, body: FolioCommentIn, principal: CurrentPrincipal, db: Db
) -> FolioThreadOut:
    """A thread at the foot (default), an inline thread on `anchor` or on the first
    occurrence of `quote`, or a reply to `thread_id`. Returns the whole thread."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    comment = await comments.create(
        db,
        principal.user,
        node,
        body=body.body,
        inline=body.inline or body.anchor is not None or body.quote is not None,
        anchor=body.anchor.model_dump() if body.anchor else None,
        quote=body.quote,
        thread_id=body.thread_id,
    )
    return await _whole(db, principal.user, comment)


@router.patch("/comments/{comment_id}", response_model=FolioThreadOut)
async def edit_comment(
    comment_id: uuid.UUID, body: FolioCommentPatch, principal: CurrentPrincipal, db: Db
) -> FolioThreadOut:
    """Edit your own comment."""
    await _reader(db, principal)
    comment = await comments.get_comment(db, principal.user, comment_id)
    await comments.edit(db, principal.user, comment, body.body)
    return await _whole(db, principal.user, comment)


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """Delete your own comment, or any as an admin of the space."""
    await _reader(db, principal)
    comment = await comments.get_comment(db, principal.user, comment_id)
    await comments.delete(db, principal.user, comment)
    return Response(status_code=204)


@router.post("/comments/{comment_id}/resolve", response_model=FolioThreadOut)
async def resolve_comment(
    comment_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> FolioThreadOut:
    """Resolve the comment's thread: it and its highlight hide, and it stays in history."""
    await _reader(db, principal)
    comment = await comments.get_comment(db, principal.user, comment_id)
    await comments.resolve(db, principal.user, comment)
    return await _whole(db, principal.user, comment)


@router.post("/comments/{comment_id}/reopen", response_model=FolioThreadOut)
async def reopen_comment(
    comment_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> FolioThreadOut:
    await _reader(db, principal)
    comment = await comments.get_comment(db, principal.user, comment_id)
    await comments.reopen(db, principal.user, comment)
    return await _whole(db, principal.user, comment)
