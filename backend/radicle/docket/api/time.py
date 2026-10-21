from uuid import UUID

from fastapi import APIRouter, Response

from radicle.docket.api.deps import CurrentPrincipal, Db
from radicle.docket.api.schemas.common import Page
from radicle.docket.api.schemas.tickets import UserRef, VoteOut, WorklogIn, WorklogOut, WorklogPatch
from radicle.docket.api.ticket_views import user_ref
from radicle.docket.db.models import ProjectRole, Worklog
from radicle.docket.services import tickets, timetracking

router = APIRouter(tags=["votes and time"])
MEMBER = ProjectRole.member


def worklog_out(worklog: Worklog, key: str) -> WorklogOut:
    return WorklogOut(
        id=str(worklog.id),
        ticket=key,
        user=user_ref(worklog.user),
        minutes=worklog.minutes,
        started_at=worklog.started_at,
        description=worklog.description,
        created_at=worklog.created_at,
        updated_at=worklog.updated_at,
    )


async def _vote(key: str, principal: CurrentPrincipal, db: Db, voted: bool) -> VoteOut:
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, write=True, permission="vote"
    )
    await timetracking.set_vote(db, access, ticket, voted)
    return VoteOut(vote_count=ticket.vote_count, voted_by_me=voted)


@router.put("/tickets/{key}/vote", response_model=VoteOut)
async def vote(key: str, principal: CurrentPrincipal, db: Db) -> VoteOut:
    """🙋 One vote per person; voting twice changes nothing. Agents do not vote."""
    return await _vote(key, principal, db, True)


@router.delete("/tickets/{key}/vote", response_model=VoteOut)
async def unvote(key: str, principal: CurrentPrincipal, db: Db) -> VoteOut:
    return await _vote(key, principal, db, False)


@router.get("/tickets/{key}/voters", response_model=Page[UserRef])
async def list_voters(key: str, principal: CurrentPrincipal, db: Db) -> Page[UserRef]:
    _, ticket = await tickets.load_ticket(db, principal.user, key)
    return Page(items=[user_ref(u) for u in await timetracking.voters(db, ticket.id)])


@router.get("/tickets/{key}/worklogs", response_model=Page[WorklogOut])
async def list_worklogs(key: str, principal: CurrentPrincipal, db: Db) -> Page[WorklogOut]:
    """Time logged on the ticket, newest first."""
    access, ticket = await tickets.load_ticket(db, principal.user, key)
    ticket_key = f"{access.project.key}-{ticket.number}"
    rows = await timetracking.list_worklogs(db, ticket)
    return Page(items=[worklog_out(w, ticket_key) for w in rows])


@router.post("/tickets/{key}/worklogs", response_model=WorklogOut, status_code=201)
async def add_worklog(key: str, body: WorklogIn, principal: CurrentPrincipal, db: Db) -> WorklogOut:
    """Log minutes worked (1 to 1440). Spent and remaining time update right away."""
    access, ticket = await tickets.load_ticket(
        db, principal.user, key, write=True, permission="worklog.create"
    )
    worklog = await timetracking.add_worklog(
        db,
        access,
        ticket,
        minutes=body.minutes,
        started_at=body.started_at,
        description=body.description,
    )
    return worklog_out(worklog, f"{access.project.key}-{ticket.number}")


@router.patch("/worklogs/{worklog_id}", response_model=WorklogOut)
async def patch_worklog(
    worklog_id: UUID, body: WorklogPatch, principal: CurrentPrincipal, db: Db
) -> WorklogOut:
    """Your own worklogs; admins can edit any."""
    wa = await timetracking.load_worklog(db, principal.user, worklog_id)
    worklog = await timetracking.update_worklog(
        db,
        wa,
        minutes=body.minutes,
        started_at=body.started_at,
        description=body.description,
        clear_description="description" in body.model_fields_set and body.description is None,
    )
    return worklog_out(worklog, f"{wa.access.project.key}-{wa.ticket.number}")


@router.delete("/worklogs/{worklog_id}", status_code=204)
async def delete_worklog(worklog_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    wa = await timetracking.load_worklog(db, principal.user, worklog_id)
    await timetracking.delete_worklog(db, wa)
    return Response(status_code=204)
