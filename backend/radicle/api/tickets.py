from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response

from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.pagination import Limit
from radicle.api.schemas.common import Page
from radicle.api.schemas.tickets import (
    ChecklistPatch,
    EventOut,
    TicketCreate,
    TicketOut,
    TicketPatch,
    TicketSummary,
)
from radicle.api.ticket_views import event_out, summaries_out, ticket_out
from radicle.core.errors import ValidationFailed
from radicle.db.models import ProjectRole
from radicle.services import history, tickets
from radicle.services.access import project_access

router = APIRouter(tags=["tickets"])

MEMBER = ProjectRole.member


@router.post("/projects/{key}/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(
    key: str, body: TicketCreate, principal: CurrentPrincipal, db: Db
) -> TicketOut:
    """Create a Task, Bug or Draft. Area is required except for drafts."""
    access = await project_access(db, principal.user, key, need=MEMBER, write=True)
    data = tickets.NewTicket(**body.model_dump())
    ticket = await tickets.create_ticket(db, access, data)
    return await ticket_out(db, ticket)


@router.get("/tickets/{key}", response_model=TicketOut)
async def get_ticket(key: str, principal: CurrentPrincipal, db: Db) -> TicketOut:
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    return await ticket_out(db, ticket)


def _expected_version(body_version: int | None, if_match: str | None) -> int:
    if body_version is not None:
        return body_version
    if if_match:
        try:
            return int(if_match.strip().strip('"').removeprefix("W/").strip('"'))
        except ValueError as exc:
            raise ValidationFailed(
                "If-Match must be the ticket version number, e.g. If-Match: 7."
            ) from exc
    raise ValidationFailed(
        "Send the version you edited as If-Match header or expected_version, so concurrent "
        "edits are not lost. GET the ticket to read its current version.",
        code="version_required",
        errors=[{"field": "expected_version", "message": "required"}],
    )


@router.patch("/tickets/{key}", response_model=TicketOut)
async def patch_ticket(
    key: str,
    body: TicketPatch,
    principal: CurrentPrincipal,
    db: Db,
    if_match: Annotated[str | None, Header()] = None,
) -> TicketOut:
    """Edit fields. Only the fields sent change and null clears one. Needs the version."""
    expected = _expected_version(body.expected_version, if_match)
    access, ticket = await tickets.load_ticket(db, principal.user, key, need=MEMBER, write=True)
    changes: dict[str, Any] = body.model_dump(exclude_unset=True, exclude={"expected_version"})
    try:
        await tickets.update_ticket(db, access, ticket, changes, expected_version=expected)
    except tickets.VersionConflict as exc:
        exc.extra["current"] = (await ticket_out(db, exc.ticket)).model_dump(mode="json")
        raise
    return await ticket_out(db, ticket)


@router.delete("/tickets/{key}", status_code=204)
async def delete_ticket(key: str, principal: CurrentPrincipal, db: Db) -> Response:
    """Soft delete. The ticket disappears from lists but its history stays."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, need=ProjectRole.admin, write=True
    )
    await tickets.delete_ticket(db, access, ticket)
    return Response(status_code=204)


@router.post("/tickets/{key}/restore", response_model=TicketOut)
async def restore_ticket(key: str, principal: CurrentPrincipal, db: Db) -> TicketOut:
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, need=ProjectRole.admin, write=True, include_deleted=True
    )
    await tickets.restore_ticket(db, access, ticket)
    return await ticket_out(db, ticket)


@router.patch("/tickets/{key}/checklist/{index}", response_model=TicketOut)
async def set_checklist_item(
    key: str, index: int, body: ChecklistPatch, principal: CurrentPrincipal, db: Db
) -> TicketOut:
    """Check or uncheck item `index` (0-based) of the description checklist."""
    access, ticket = await tickets.load_ticket(db, principal.user, key, need=MEMBER, write=True)
    await tickets.set_checklist_item(db, access, ticket, index, body.checked)
    return await ticket_out(db, ticket)


@router.get("/tickets/{key}/children", response_model=Page[TicketSummary])
async def list_children(key: str, principal: CurrentPrincipal, db: Db) -> Page[TicketSummary]:
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    return Page(items=await summaries_out(db, await tickets.list_children(db, ticket)))


@router.put("/tickets/{key}/collaborators/{handle}", response_model=TicketOut)
async def add_collaborator(key: str, handle: str, principal: CurrentPrincipal, db: Db) -> TicketOut:
    access, ticket = await tickets.load_ticket(db, principal.user, key, need=MEMBER, write=True)
    await tickets.add_collaborator(db, access, ticket, handle)
    return await ticket_out(db, ticket)


@router.delete("/tickets/{key}/collaborators/{handle}", response_model=TicketOut)
async def remove_collaborator(
    key: str, handle: str, principal: CurrentPrincipal, db: Db
) -> TicketOut:
    access, ticket = await tickets.load_ticket(db, principal.user, key, need=MEMBER, write=True)
    await tickets.remove_collaborator(db, access, ticket, handle)
    return await ticket_out(db, ticket)


@router.get("/tickets/{key}/history", response_model=Page[EventOut])
async def get_history(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    limit: Limit = 50,
    cursor: Annotated[str | None, Query(description="next_cursor of the previous page")] = None,
) -> Page[EventOut]:
    """Ticket events, newest first."""
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    before = _int_cursor(cursor)
    events = await history.list_events(db, ticket.id, limit=limit + 1, before_id=before)
    page = events[:limit]
    next_cursor = str(page[-1].id) if len(events) > limit else None
    return Page(items=[event_out(e) for e in page], next_cursor=next_cursor)


def _int_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    if not cursor.isdigit():
        raise ValidationFailed("Invalid cursor. Use next_cursor from the previous page.")
    return int(cursor)
