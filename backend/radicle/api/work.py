from typing import Any
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.api.deps import CurrentPrincipal, Db, HumanUser
from radicle.api.schemas.common import Input, Output, Page, UtcDatetime
from radicle.api.schemas.tickets import TicketOut, UserRef
from radicle.api.ticket_views import ticket_out, user_ref
from radicle.db.models import FilterVisibility, Project, ProjectRole, SavedFilter, TicketType
from radicle.services import filters, preferences, ranking, tickets

router = APIRouter(tags=["filters, ranking and preferences"])


class FilterOut(Output):
    id: str
    name: str
    rql: str
    visibility: FilterVisibility
    project: str | None
    owner: UserRef
    mine: bool
    created_at: UtcDatetime
    updated_at: UtcDatetime


class FilterIn(Input):
    name: str
    rql: str
    visibility: FilterVisibility = FilterVisibility.private
    project: str | None = Field(default=None, description="Required for visibility=project")


class FilterPatch(Input):
    name: str | None = None
    rql: str | None = None
    visibility: FilterVisibility | None = None
    project: str | None = None


class RankIn(Input):
    before: str | None = Field(default=None, description="Ticket key to go right above")
    after: str | None = Field(default=None, description="Ticket key to go right below")


class NextIn(Input):
    project: str | None = None
    area: str | None = None
    type: TicketType | None = None
    claim: bool = Field(default=False, description="Assign it to you and start it, atomically")


class NextOut(Output):
    ticket: TicketOut | None = Field(description="null when nothing is ready to work on")


class PreferencesOut(Output):
    theme: str
    language: str | None
    shortcuts: bool
    density: str


async def filter_out(db: Db, row: SavedFilter, user_id: UUID) -> FilterOut:
    project = await db.get(Project, row.project_id) if row.project_id else None
    return FilterOut(
        id=str(row.id),
        name=row.name,
        rql=row.rql,
        visibility=row.visibility,
        project=project.key if project else None,
        owner=user_ref(row.owner),
        mine=row.owner_id == user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/filters", response_model=Page[FilterOut])
async def list_filters(
    principal: CurrentPrincipal, db: Db, project: str | None = None
) -> Page[FilterOut]:
    """Filters you can see: yours, your projects' and the instance's. With `project`,
    only project filters of that project."""
    rows = await filters.list_filters(db, principal.user, project)
    return Page(items=[await filter_out(db, r, principal.user.id) for r in rows])


@router.post("/filters", response_model=FilterOut, status_code=201)
async def create_filter(body: FilterIn, principal: CurrentPrincipal, db: Db) -> FilterOut:
    row = await filters.create_filter(
        db,
        principal.user,
        name=body.name,
        rql=body.rql,
        visibility=body.visibility,
        project=body.project,
    )
    return await filter_out(db, row, principal.user.id)


@router.patch("/filters/{filter_id}", response_model=FilterOut)
async def patch_filter(
    filter_id: UUID, body: FilterPatch, principal: CurrentPrincipal, db: Db
) -> FilterOut:
    """Only the owner. To change someone else's filter, save a copy."""
    row = await filters.get_filter(db, principal.user, filter_id)
    row = await filters.update_filter(
        db,
        principal.user,
        row,
        name=body.name,
        rql=body.rql,
        visibility=body.visibility,
        project=body.project,
    )
    return await filter_out(db, row, principal.user.id)


@router.delete("/filters/{filter_id}", status_code=204)
async def delete_filter(filter_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    row = await filters.get_filter(db, principal.user, filter_id)
    await filters.delete_filter(db, principal.user, row)
    return Response(status_code=204)


@router.post("/tickets/next", response_model=NextOut)
async def next_ticket(body: NextIn, principal: CurrentPrincipal, db: Db) -> NextOut:
    """The highest-ranked ticket ready to work on: to do, not blocked, unassigned or yours.
    With `claim`, it is assigned to you and moved to in progress; parallel callers never
    get the same ticket."""
    found = await ranking.next_ticket(
        db,
        principal.user,
        project=body.project,
        area=body.area,
        ticket_type=body.type.value if body.type else None,
        claim=body.claim,
    )
    if found is None:
        return NextOut(ticket=None)
    return NextOut(ticket=await ticket_out(db, found[1], viewer=principal.user))


@router.post("/tickets/{key}/rank", response_model=TicketOut)
async def rank_ticket(key: str, body: RankIn, principal: CurrentPrincipal, db: Db) -> TicketOut:
    """Move the ticket right before or after another ticket of the same project."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, need=ProjectRole.member, write=True
    )
    await ranking.rank_ticket(db, access, ticket, before=body.before, after=body.after)
    return await ticket_out(db, ticket, viewer=principal.user)


@router.get("/me/preferences", response_model=PreferencesOut)
async def get_preferences(user: HumanUser, db: Db) -> PreferencesOut:
    return PreferencesOut(**await preferences.get_preferences(db, user))


@router.patch("/me/preferences", response_model=PreferencesOut)
async def patch_preferences(body: dict[str, Any], user: HumanUser, db: Db) -> PreferencesOut:
    """theme (system, light, dark), language (en, es or null), shortcuts, density."""
    return PreferencesOut(**await preferences.update_preferences(db, user, body))
