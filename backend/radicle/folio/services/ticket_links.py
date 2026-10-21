"""Docs linked to Docket tickets (Folio 4.1 and 4.2).

Folio keeps only the ticket's id; the ticket itself is read with `radicle.docket.public`
and the reader's own Docket access, so a ticket they can't see shows as restricted. Docs
are filtered the same way from the other side: the Docs panel of a ticket lists only the
pages the reader may see."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.docket_links import FolioTicketLink, TicketLinkKind
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import access
from radicle.platform.config import get_settings
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed

# Keys as people write them in prose: PA-4, RAD-38 (not inside words or longer numbers).
KEY_IN_TEXT = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]{1,9}-\d{1,9})(?![\w-])")
ANCHOR = re.compile(r"^[a-z0-9][a-z0-9-]{0,199}$")
MAX_MENTIONS = 200
TITLE_MAX = 120


@dataclass(frozen=True)
class Link:
    link: FolioTicketLink
    ticket: docket.TicketSummary | None  # None: the reader can't see it


@dataclass(frozen=True)
class LinkedDoc:
    link: FolioTicketLink
    node: FolioNode
    space_key: str


def page_path(node: FolioNode, anchor: str | None = None) -> str:
    return f"/folio/p/{node.id}-{node.slug}" + (f"#{anchor}" if anchor else "")


def _check_anchor(anchor: str | None) -> str | None:
    if anchor is None or anchor == "":
        return None
    if not ANCHOR.fullmatch(anchor):
        raise ValidationFailed(
            "anchor is a section's heading anchor, like conecta-un-agente.",
            errors=[{"field": "anchor", "message": "invalid"}],
        )
    return anchor


async def _ticket(db: AsyncSession, user: User, key: str) -> docket.TicketSummary:
    found = (await docket.get_tickets(db, [key], user)).get(key.strip().upper())
    if found is None:
        raise NotFound(
            f"Ticket {key.strip().upper()} not found, or you can't see it in Docket.",
            code="ticket_not_found",
        )
    return found


async def links_for_node(db: AsyncSession, user: User, node: FolioNode) -> list[Link]:
    """The doc's links, oldest first, each with the ticket as the reader sees it."""
    rows = list(
        await db.scalars(
            select(FolioTicketLink)
            .where(FolioTicketLink.node_id == node.id)
            .order_by(FolioTicketLink.created_at, FolioTicketLink.id)
        )
    )
    seen = await docket.get_tickets_by_id(db, [r.ticket_id for r in rows], user)
    return [Link(r, seen.get(r.ticket_id)) for r in rows]


async def upsert(
    db: AsyncSession,
    node: FolioNode,
    ticket_id: uuid.UUID,
    kind: TicketLinkKind,
    user: User,
    anchor: str | None,
    item_key: str | None = None,
) -> FolioTicketLink:
    await db.execute(
        insert(FolioTicketLink)
        .values(
            id=uuid.uuid4(),
            node_id=node.id,
            ticket_id=ticket_id,
            kind=kind,
            anchor=anchor,
            item_key=item_key,
            created_by=user.id,
        )
        .on_conflict_do_nothing(constraint="uq_folio_ticket_links")
    )
    return await db.scalar(
        select(FolioTicketLink).where(
            FolioTicketLink.node_id == node.id,
            FolioTicketLink.ticket_id == ticket_id,
            FolioTicketLink.kind == kind,
        )
    )  # type: ignore[return-value]  # the row exists: just inserted or already there


async def link(
    db: AsyncSession, user: User, node: FolioNode, key: str, *, anchor: str | None = None
) -> Link:
    """Link the doc (or one of its sections) to a ticket by hand; linking twice is a no-op."""
    await access.require_edit(db, user, node)
    ticket = await _ticket(db, user, key)
    row = await upsert(db, node, ticket.id, TicketLinkKind.manual, user, _check_anchor(anchor))
    return Link(row, ticket)


async def unlink(db: AsyncSession, user: User, node: FolioNode, link_id: uuid.UUID) -> None:
    await access.require_edit(db, user, node)
    row = await db.get(FolioTicketLink, link_id)
    if row is None or row.node_id != node.id:
        raise NotFound(f"Link {link_id} not found on this page.", code="ticket_link_not_found")
    await db.delete(row)
    await db.flush()


async def unlink_key(db: AsyncSession, user: User, node: FolioNode, key: str) -> int:
    """Remove every link from the doc to this ticket; returns how many."""
    await access.require_edit(db, user, node)
    ticket = await _ticket(db, user, key)
    result = await db.execute(
        delete(FolioTicketLink).where(
            FolioTicketLink.node_id == node.id, FolioTicketLink.ticket_id == ticket.id
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def docs_for_ticket(db: AsyncSession, user: User, key: str) -> list[LinkedDoc]:
    """Docs linked to a ticket that the reader may see, newest link first."""
    ticket = await _ticket(db, user, key)
    rows = await db.execute(
        select(FolioTicketLink, FolioNode, FolioSpace.key)
        .join(FolioNode, FolioNode.id == FolioTicketLink.node_id)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .where(FolioTicketLink.ticket_id == ticket.id, await access.node_filter(db, user))
        .order_by(FolioTicketLink.created_at.desc(), FolioTicketLink.id)
    )
    return [LinkedDoc(link, node, space) for link, node, space in rows]


def keys_in(text: str) -> list[str]:
    """Ticket keys in a doc's plain text, in order of first appearance."""
    return list(dict.fromkeys(KEY_IN_TEXT.findall(text)))[:MAX_MENTIONS]


async def record_mentions(db: AsyncSession, node: FolioNode, text: str, author: User) -> None:
    """After a publish: the doc's `mention` links are the tickets its text names now, among
    those the author can see. Other kinds of links are left alone."""
    found = await docket.get_tickets(db, keys_in(text), author)
    ids = {t.id for t in found.values() if t is not None}
    await db.execute(
        delete(FolioTicketLink).where(
            FolioTicketLink.node_id == node.id,
            FolioTicketLink.kind == TicketLinkKind.mention,
            FolioTicketLink.ticket_id.not_in(ids) if ids else true(),
        )
    )
    for ticket_id in ids:
        await upsert(db, node, ticket_id, TicketLinkKind.mention, author, None)


@dataclass
class FromText:
    text: str
    project: str
    title: str | None = None
    anchor: str | None = None
    type: str = "task"
    area: str | None = None
    milestone: str | None = None


def _title(data: FromText) -> str:
    title = (data.title or "").strip() or data.text.strip().splitlines()[0].strip()
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rstrip() + "…"


async def create_from_text(db: AsyncSession, user: User, node: FolioNode, data: FromText) -> Link:
    """A ticket made from a selection or an action item, linked to that section. Whoever
    can read the doc may do it if Docket lets them create tickets in the project."""
    if not data.text.strip():
        raise ValidationFailed(
            "Send the selected text (or the action item) in text.",
            errors=[{"field": "text", "message": "required"}],
        )
    anchor = _check_anchor(data.anchor)
    url = get_settings().base_url.rstrip("/") + page_path(node, anchor)
    quote = "\n".join(f"> {line}" for line in data.text.strip().splitlines())
    ticket = await docket.create_ticket(
        db,
        docket.NewTicket(
            project=data.project,
            title=_title(data),
            description_md=f"{quote}\n\nFrom [{node.title}]({url}).",
            type=data.type,
            area=data.area,
            milestone=data.milestone,
        ),
        user,
    )
    row = await upsert(db, node, ticket.id, TicketLinkKind.created_from_text, user, anchor)
    return Link(row, ticket)
