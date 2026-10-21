"""Docket tickets inside docs over REST (Folio 4.1, 4.2): live previews for smart links, a
ticket table by Docket RQL, a doc's ticket links, a ticket's docs, and creating a ticket
from a selection. Tickets are always read with the caller's Docket access."""

import uuid
from typing import Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

import radicle.docket.public as docket
from radicle.folio.api.spaces import NodeRef, _ref
from radicle.folio.services import docket_docs, nodes, ticket_links
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.errors import ValidationFailed

router = APIRouter(tags=["folio"])

LinkKind = Literal["mention", "created_from_text", "build_spec_item", "manual"]


class FolioTicketAssignee(Output):
    handle: str
    display_name: str


class FolioTicketOut(Output):
    key: str
    title: str
    type: str
    status: str
    status_category: Literal["todo", "in_progress", "done"]
    priority: str
    assignee: FolioTicketAssignee | None
    area: str | None
    milestone: str | None
    checklist_done: int
    checklist_total: int
    url: str = Field(description="The ticket in Docket, e.g. /t/PA-4")


class FolioTicketPreview(Output):
    key: str = Field(description="As asked, upper-cased")
    restricted: bool = Field(description="Not found, or you can't see it in Docket")
    ticket: FolioTicketOut | None


class FolioTicketPreviewsOut(Output):
    items: list[FolioTicketPreview]


class FolioTicketQueryOut(Output):
    items: list[FolioTicketOut]
    total: int


class FolioTicketLinkOut(Output):
    id: uuid.UUID
    kind: LinkKind
    anchor: str | None
    item_key: str | None
    restricted: bool = Field(description="You can't see the ticket in Docket")
    ticket: FolioTicketOut | None
    created_at: UtcDatetime


class FolioTicketLinksOut(Output):
    items: list[FolioTicketLinkOut]


class FolioTicketLinkIn(Input):
    key: str = Field(min_length=3, max_length=30, examples=["PA-4"])
    anchor: str | None = Field(default=None, max_length=200, examples=["conecta-un-agente"])


class TicketFromTextIn(Input):
    text: str = Field(min_length=1, max_length=5000, description="The selection or action item")
    anchor: str | None = Field(default=None, max_length=200, description="Its section")
    project: str = Field(min_length=1, max_length=10, examples=["PA"])
    title: str | None = Field(default=None, max_length=255, description="Else the first line")
    type: Literal["task", "bug", "draft"] = "task"
    area: str | None = Field(default=None, max_length=100)
    milestone: str | None = Field(default=None, max_length=100)


class TicketDocOut(Output):
    node: NodeRef
    space: str
    kind: LinkKind | None = Field(
        description="How it links to a ticket; null for a milestone or area"
    )
    anchor: str | None
    url: str = Field(description="The doc, at the linked section when there is one")
    description: str | None = Field(
        default=None, description="For a milestone or area: the doc's published description"
    )


class TicketDocsOut(Output):
    items: list[TicketDocOut]


def ticket_out(t: docket.TicketSummary) -> FolioTicketOut:
    assignee = (
        FolioTicketAssignee(handle=t.assignee_handle, display_name=t.assignee_name or "")
        if t.assignee_handle
        else None
    )
    return FolioTicketOut(
        key=t.key,
        title=t.title,
        type=t.type,
        status=t.status,
        status_category=t.status_category,
        priority=t.priority,
        assignee=assignee,
        area=t.area,
        milestone=t.milestone,
        checklist_done=t.checklist_done,
        checklist_total=t.checklist_total,
        url=f"/t/{t.key}",
    )


def link_out(found: ticket_links.Link) -> FolioTicketLinkOut:
    row = found.link
    return FolioTicketLinkOut(
        id=row.id,
        kind=row.kind.value,
        anchor=row.anchor,
        item_key=row.item_key,
        restricted=found.ticket is None,
        ticket=ticket_out(found.ticket) if found.ticket else None,
        created_at=row.created_at,
    )


async def require_reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/tickets/preview", response_model=FolioTicketPreviewsOut)
async def preview_tickets(
    principal: CurrentPrincipal,
    db: Db,
    keys: str = Query(min_length=3, max_length=2000, description="Comma-separated: PA-4,PA-7"),
) -> FolioTicketPreviewsOut:
    """Live status, assignee and checklist of tickets for smart links, in the order asked.
    A ticket you can't see in Docket comes back restricted, with no title."""
    await require_reader(db, principal)
    asked = [k for k in (part.strip() for part in keys.split(",")) if k]
    if len(asked) > docket.MAX_KEYS:
        raise ValidationFailed(
            f"Ask at most {docket.MAX_KEYS} keys at a time.",
            errors=[{"field": "keys", "message": "too many"}],
        )
    found = await docket.get_tickets(db, asked, principal.user)
    return FolioTicketPreviewsOut(
        items=[
            FolioTicketPreview(key=key, restricted=t is None, ticket=ticket_out(t) if t else None)
            for key, t in found.items()
        ]
    )


@router.get("/tickets/query", response_model=FolioTicketQueryOut)
async def query_tickets(
    principal: CurrentPrincipal,
    db: Db,
    rql: str = Query(min_length=1, max_length=2000, examples=["project = PA AND status != Done"]),
    limit: int = Query(default=25, ge=1, le=100),
) -> FolioTicketQueryOut:
    """The ticket table block: Docket's RQL, only the tickets you can see in Docket."""
    await require_reader(db, principal)
    result = await docket.search(db, rql, principal.user, limit=limit)
    return FolioTicketQueryOut(items=[ticket_out(t) for t in result.tickets], total=result.total)


@router.get("/nodes/{node_id}/ticket-links", response_model=FolioTicketLinksOut)
async def list_ticket_links(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> FolioTicketLinksOut:
    """The doc's tickets: mentioned, created from its text, from its deliverables or linked
    by hand."""
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    found = await ticket_links.links_for_node(db, principal.user, node)
    return FolioTicketLinksOut(items=[link_out(f) for f in found])


@router.post("/nodes/{node_id}/ticket-links", response_model=FolioTicketLinkOut, status_code=201)
async def add_ticket_link(
    node_id: uuid.UUID, body: FolioTicketLinkIn, principal: CurrentPrincipal, db: Db
) -> FolioTicketLinkOut:
    """Link the doc, or one of its sections, to a ticket. Needs edit on the page."""
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    found = await ticket_links.link(db, principal.user, node, body.key, anchor=body.anchor)
    return link_out(found)


@router.delete("/nodes/{node_id}/ticket-links/{link_id}", status_code=204)
async def remove_ticket_link(
    node_id: uuid.UUID, link_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    await ticket_links.unlink(db, principal.user, node, link_id)
    return Response(status_code=204)


@router.post("/nodes/{node_id}/tickets", response_model=FolioTicketLinkOut, status_code=201)
async def create_ticket_from_text(
    node_id: uuid.UUID, body: TicketFromTextIn, principal: CurrentPrincipal, db: Db
) -> FolioTicketLinkOut:
    """Create a Docket ticket from a selection or an action item, linked to its section.
    Whoever can read the doc may, if Docket lets them create tickets in the project."""
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    found = await ticket_links.create_from_text(
        db,
        principal.user,
        node,
        ticket_links.FromText(
            text=body.text,
            project=body.project,
            title=body.title,
            anchor=body.anchor,
            type=body.type,
            area=body.area,
            milestone=body.milestone,
        ),
    )
    return link_out(found)


@router.get("/links", response_model=TicketDocsOut)
async def docs_for_ticket(
    principal: CurrentPrincipal,
    db: Db,
    ticket: str | None = Query(default=None, min_length=3, max_length=30, examples=["PA-4"]),
    milestone: str | None = Query(default=None, max_length=120, examples=["PA:V1"]),
    area: str | None = Query(default=None, max_length=120, examples=["PA:Backend"]),
) -> TicketDocsOut:
    """The docs you may see that are linked to a ticket, or that name a milestone or an area
    in their metadata (the Docs panels in Docket). Pass exactly one of the three."""
    await require_reader(db, principal)
    if sum(v is not None for v in (ticket, milestone, area)) != 1:
        raise ValidationFailed(
            "Pass one of ticket=PA-4, milestone=PA:V1 or area=PA:Backend.",
            errors=[{"field": "ticket", "message": "one of ticket, milestone, area"}],
        )
    if ticket is None:
        named = await (
            docket_docs.docs_for_milestone(db, principal.user, milestone)
            if milestone is not None
            else docket_docs.docs_for_area(db, principal.user, area or "")
        )
        return TicketDocsOut(
            items=[
                TicketDocOut(
                    node=_ref(d.node),
                    space=d.space_key,
                    kind=None,
                    anchor=None,
                    url=ticket_links.page_path(d.node),
                    description=d.description,
                )
                for d in named
            ]
        )
    found = await ticket_links.docs_for_ticket(db, principal.user, ticket)
    return TicketDocsOut(
        items=[
            TicketDocOut(
                node=_ref(d.node),
                space=d.space_key,
                kind=d.link.kind.value,
                anchor=d.link.anchor,
                url=ticket_links.page_path(d.node, d.link.anchor),
            )
            for d in found
        ]
    )
