from fastapi import APIRouter, Query
from pydantic import Field

from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.schemas.common import Input, Output
from radicle.api.schemas.tickets import TicketOut, TicketSummary
from radicle.api.ticket_views import summaries_out, ticket_out
from radicle.db.models import Classification, Origin, Priority, TicketType
from radicle.services import inbox, tickets
from radicle.services.access import project_access

router = APIRouter(tags=["inbox"])


class InboxOut(Output):
    tab: inbox.Tab
    counts: dict[str, int] = Field(description="Items per tab: new, in_review, approved, discarded")
    items: list[TicketSummary]


class ApproveIn(Input):
    type: TicketType = Field(description="task or bug")
    area: str
    milestone: str | None = None
    priority: Priority | None = None
    assignee: str | None = None


class DiscardIn(Input):
    public_comment: str | None = Field(
        default=None, description="Shown to the submitter on the tracking page"
    )


class DuplicateIn(Input):
    original: str = Field(description="Key of the ticket it duplicates")


@router.get("/projects/{key}/inbox", response_model=InboxOut)
async def get_inbox(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    tab: inbox.Tab = "new",
    classification: Classification | None = None,
    origin: Origin | None = None,
    sort: inbox.Sort = Query(default="votes", description="votes, age or score (impact*2-effort)"),
) -> InboxOut:
    """The project's drafts: new, in review, approved (converted) or discarded."""
    access = await project_access(db, principal.user, key)
    view = await inbox.inbox(
        db,
        principal.user,
        access.project,
        tab=tab,
        classification=classification,
        origin=origin,
        sort=sort,
    )
    return InboxOut(tab=tab, counts=view.counts, items=await summaries_out(db, view.tickets))


@router.post("/tickets/{key}/inbox/approve", response_model=TicketOut)
async def approve(key: str, body: ApproveIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Approve and convert in one step: the draft becomes a task or bug in the same ticket,
    keeping origin, classification, votes, comments and history."""
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.approve(
        db,
        access,
        ticket,
        key,
        to_type=body.type,
        area=body.area,
        milestone=body.milestone,
        priority=body.priority,
        assignee=body.assignee,
    )
    return await ticket_out(db, ticket, viewer=principal.user)


@router.post("/tickets/{key}/inbox/discard", response_model=TicketOut)
async def discard(key: str, body: DiscardIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.discard(db, access, ticket, key, public_comment=body.public_comment)
    return await ticket_out(db, ticket, viewer=principal.user)


@router.post("/tickets/{key}/inbox/duplicate", response_model=TicketOut)
async def duplicate(key: str, body: DuplicateIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Link as duplicate of `original`, close it and pass its voters to the original."""
    access, ticket = await tickets.load_ticket(db, principal.user, key, write=True)
    await inbox.mark_duplicate(db, access, ticket, key, body.original)
    return await ticket_out(db, ticket, viewer=principal.user)
