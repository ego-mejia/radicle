"""Build spec to tickets over REST (Folio 4.3): the deliverables a build-spec doc lists,
with their tickets, and creating a Docket task for each one chosen."""

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.api.tickets import FolioTicketOut, require_reader, ticket_out
from radicle.folio.services import build_spec, nodes
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output

router = APIRouter(tags=["folio"])


class BuildSpecItemOut(Output):
    key: str = Field(description="The deliverable's number, e.g. 4.1")
    title: str
    description: str
    criteria: list[str] = Field(description="Acceptance criteria, the ticket's checklist")
    anchor: str | None = Field(description="Its section's heading anchor")
    linked: bool = Field(description="A ticket was already created for it")
    restricted: bool = Field(description="Linked, but you can't see the ticket in Docket")
    ticket: FolioTicketOut | None


class BuildSpecItemsOut(Output):
    items: list[BuildSpecItemOut]


class BuildSpecTicketsIn(Input):
    project: str = Field(min_length=1, max_length=10, examples=["PA"])
    keys: list[str] | None = Field(
        default=None, max_length=50, description="Deliverables to send; omit for all new ones"
    )
    type: Literal["task", "bug", "draft"] = "task"
    area: str | None = Field(default=None, max_length=100)
    milestone: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)
    dry_run: bool = Field(default=False, description="List what would be created, create none")


def item_out(found: build_spec.ItemWithTicket) -> BuildSpecItemOut:
    item = found.item
    return BuildSpecItemOut(
        key=item.key,
        title=item.title,
        description=item.description,
        criteria=item.criteria,
        anchor=item.anchor,
        linked=found.linked,
        restricted=found.linked and found.ticket is None,
        ticket=ticket_out(found.ticket) if found.ticket else None,
    )


@router.get("/nodes/{node_id}/build-spec/items", response_model=BuildSpecItemsOut)
async def build_spec_items(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> BuildSpecItemsOut:
    """The deliverables of a build-spec doc (its deliverables table, or numbered level-3
    headings) and each one's ticket, live. Feeds the wizard and the Ticket progress block."""
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    found = await build_spec.items(db, principal.user, node)
    return BuildSpecItemsOut(items=[item_out(f) for f in found])


@router.post(
    "/nodes/{node_id}/build-spec/tickets", response_model=BuildSpecItemsOut, status_code=201
)
async def create_build_spec_tickets(
    node_id: uuid.UUID, body: BuildSpecTicketsIn, principal: CurrentPrincipal, db: Db
) -> BuildSpecItemsOut:
    """One Docket task per chosen deliverable that has none yet, with a link to its section
    and its criteria as a checklist. Running it again creates only the new ones. Needs edit
    on the doc and Docket's ticket.create in the project."""
    await require_reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    choice = build_spec.Choice(
        project=body.project,
        keys=body.keys,
        type=body.type,
        area=body.area,
        milestone=body.milestone,
        tags=body.tags,
    )
    made = await build_spec.create_tickets(db, principal.user, node, choice, dry_run=body.dry_run)
    return BuildSpecItemsOut(items=[item_out(m) for m in made])
