from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response

from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.pagination import Limit, decode_cursor, encode_cursor
from radicle.api.schemas.common import Page
from radicle.api.schemas.tickets import (
    CommentIn,
    CommentOut,
    LinkCreate,
    LinkOut,
    ReactionOut,
)
from radicle.api.ticket_views import ctx_ref, user_ref
from radicle.db.models import Comment, LinkType, ProjectRole
from radicle.platform.errors import ValidationFailed
from radicle.services import comments, relations, tickets

router = APIRouter(tags=["links and comments"])
MEMBER = ProjectRole.member


def _link_type(value: str) -> LinkType:
    try:
        return LinkType(value.strip().lower().replace(" ", "_"))
    except ValueError as exc:
        raise ValidationFailed(
            f"Unknown link type '{value}'. Use blocks, relates_to, duplicates or clones.",
            errors=[{"field": "type", "message": "invalid"}],
        ) from exc


@router.get("/tickets/{key}/links", response_model=list[LinkOut])
async def list_links(key: str, principal: CurrentPrincipal, db: Db) -> list[LinkOut]:
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    return [
        LinkOut(id=str(v.id), type=v.type, label=v.label, ticket=ctx_ref(v.other))
        for v in await relations.links_for(db, ticket, principal.user)
    ]


@router.post("/tickets/{key}/links", response_model=list[LinkOut], status_code=201)
async def create_link(
    key: str, body: LinkCreate, principal: CurrentPrincipal, db: Db
) -> list[LinkOut]:
    """Link this ticket to another. `blocks` means this ticket blocks the target.

    Returns the ticket's links after the change.
    """
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, write=True, permission="link.manage"
    )
    await relations.add_link(db, access, ticket, _link_type(body.type), body.target)
    return await list_links(key, principal, db)


@router.delete("/links/{link_id}", status_code=204)
async def delete_link(link_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    await relations.remove_link(db, principal.user, link_id)
    return Response(status_code=204)


async def _comments_out(db: Db, key: str, rows: list[Comment]) -> list[CommentOut]:
    reactions = await comments.reactions_for(db, [c.id for c in rows if c.deleted_at is None])
    return [
        CommentOut(
            id=str(c.id),
            ticket=key,
            author=user_ref(c.author),
            body_md="" if c.deleted_at else c.body_md,
            created_at=c.created_at,
            edited_at=c.edited_at,
            deleted=c.deleted_at is not None,
            reactions=[
                ReactionOut(emoji=r.emoji, count=r.count, users=r.users)
                for r in reactions.get(c.id, [])
            ],
        )
        for c in rows
    ]


@router.get("/tickets/{key}/comments", response_model=Page[CommentOut])
async def list_comments(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    limit: Limit = 50,
    cursor: str | None = None,
    order: Annotated[Literal["asc", "desc"], Query(description="asc = oldest first")] = "asc",
) -> Page[CommentOut]:
    """Comments of a ticket. Deleted comments stay as placeholders with an empty body."""
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    rows = await comments.list_comments(
        db, ticket, limit=limit + 1, newest_first=order == "desc", after=decode_cursor(cursor)
    )
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if len(rows) > limit else None
    return Page(items=await _comments_out(db, key.upper(), page), next_cursor=next_cursor)


@router.post("/tickets/{key}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    key: str, body: CommentIn, principal: CurrentPrincipal, db: Db
) -> CommentOut:
    """Comment in markdown. @handles outside code are recorded as mentions."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, write=True, permission="comment.create"
    )
    comment = await comments.add_comment(db, access, ticket, body.body_md)
    return (await _comments_out(db, key.upper(), [comment]))[0]


async def _comment_key(db: Db, ca: comments.CommentAccess) -> str:
    return f"{ca.access.project.key}-{ca.ticket.number}"


@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: UUID, body: CommentIn, principal: CurrentPrincipal, db: Db
) -> CommentOut:
    """Only the author can edit."""
    ca = await comments.load_comment(db, principal.user, comment_id, permission="comment.create")
    comment = await comments.edit_comment(db, ca, body.body_md)
    return (await _comments_out(db, await _comment_key(db, ca), [comment]))[0]


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """The author or a project admin can delete. History records 'comment deleted'."""
    ca = await comments.load_comment(db, principal.user, comment_id, write=True)
    await comments.delete_comment(db, ca)
    return Response(status_code=204)


@router.put("/comments/{comment_id}/reactions/{emoji}", response_model=CommentOut)
async def add_reaction(
    comment_id: UUID, emoji: str, principal: CurrentPrincipal, db: Db
) -> CommentOut:
    ca = await comments.load_comment(db, principal.user, comment_id, permission="comment.create")
    await comments.set_reaction(db, ca, emoji, True)
    return (await _comments_out(db, await _comment_key(db, ca), [ca.comment]))[0]


@router.delete("/comments/{comment_id}/reactions/{emoji}", response_model=CommentOut)
async def remove_reaction(
    comment_id: UUID, emoji: str, principal: CurrentPrincipal, db: Db
) -> CommentOut:
    ca = await comments.load_comment(db, principal.user, comment_id, permission="comment.create")
    await comments.set_reaction(db, ca, emoji, False)
    return (await _comments_out(db, await _comment_key(db, ca), [ca.comment]))[0]
