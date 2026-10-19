from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from radicle.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.api.schemas.common import Page
from radicle.api.schemas.sprints import (
    BacklogOut,
    SprintComplete,
    SprintCompleteOut,
    SprintCreate,
    SprintDetail,
    SprintKeys,
    SprintKeysOut,
    SprintOut,
    SprintPatch,
    SprintReport,
    SprintStart,
    report_out,
)
from radicle.api.ticket_views import summaries_out
from radicle.db.models import BoardQuickFilter, Project, ProjectRole, Sprint, SprintState, Ticket
from radicle.services import boards, search, sprints

router = APIRouter(tags=["sprints"])
ADMIN = ProjectRole.admin
MEMBER = ProjectRole.member


def _out(s: Sprint, st: sprints.SprintStats) -> SprintOut:
    capacity = float(s.capacity_hours) if s.capacity_hours is not None else None
    return SprintOut(
        id=str(s.id),
        board_id=str(s.board_id),
        name=s.name,
        goal=s.goal,
        state=s.state,
        start_date=s.start_date,
        end_date=s.end_date,
        capacity_hours=capacity,
        started_at=s.started_at,
        completed_at=s.completed_at,
        position=s.position,
        goal_met=s.goal_met,
        ticket_count=st.tickets,
        done_count=st.done,
        estimate_hours=float(st.estimate_hours),
        remaining_hours=float(st.remaining_hours),
        unestimated_count=st.unestimated,
        over_capacity=capacity is not None and float(st.estimate_hours) > capacity,
    )


async def sprint_out(db: Db, principal: CurrentPrincipal, sprint: Sprint) -> SprintOut:
    st = await sprints.stats(db, principal.user, [sprint])
    return _out(sprint, st[sprint.id])


@router.get("/boards/{board_id}/sprints", response_model=Page[SprintOut])
async def list_sprints(
    board_id: UUID, principal: CurrentPrincipal, db: Db, state: SprintState | None = None
) -> Page[SprintOut]:
    """Active first, then future in plan order, then closed (newest first)."""
    ba = await boards.load_board(db, principal.user, board_id)
    rows = await sprints.list_sprints(db, ba.board, state)
    st = await sprints.stats(db, principal.user, rows)
    return Page(items=[_out(s, st[s.id]) for s in rows])


@router.post("/boards/{board_id}/sprints", response_model=SprintOut, status_code=201)
async def create_sprint(
    board_id: UUID, body: SprintCreate, principal: CurrentPrincipal, db: Db
) -> SprintOut:
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="sprint.manage"
    )
    sprint = await sprints.create_sprint(db, ba, sprints.SprintSpec(**body.model_dump()))
    return await sprint_out(db, principal, sprint)


@router.get("/sprints/{sprint_id}", response_model=SprintDetail)
async def get_sprint(sprint_id: UUID, principal: CurrentPrincipal, db: Db) -> SprintDetail:
    _, sprint = await sprints.load_sprint(db, principal.user, sprint_id)
    out = await sprint_out(db, principal, sprint)
    items = await sprints.sprint_tickets(db, principal.user, sprint)
    return SprintDetail(**out.model_dump(), tickets=await summaries_out(db, items))


@router.patch("/sprints/{sprint_id}", response_model=SprintOut)
async def patch_sprint(
    sprint_id: UUID, body: SprintPatch, principal: CurrentPrincipal, db: Db
) -> SprintOut:
    """Future: everything. Active: goal, end date and capacity. Closed: only goal_met."""
    _, sprint = await sprints.load_sprint(
        db, principal.user, sprint_id, write=True, permission="sprint.manage"
    )
    await sprints.update_sprint(db, sprint, body.model_dump(exclude_unset=True))
    return await sprint_out(db, principal, sprint)


@router.delete("/sprints/{sprint_id}", status_code=204)
async def delete_sprint(sprint_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    _, sprint = await sprints.load_sprint(
        db, principal.user, sprint_id, write=True, permission="sprint.manage"
    )
    await sprints.delete_sprint(db, principal.user, sprint)
    return Response(status_code=204)


@router.post("/sprints/{sprint_id}/start", response_model=SprintOut)
async def start_sprint(
    sprint_id: UUID, body: SprintStart, principal: CurrentPrincipal, db: Db
) -> SprintOut:
    """Needs dates (1 to 28 days). Saves each ticket's estimate and remaining as the commitment."""
    _, sprint = await sprints.load_sprint(
        db, principal.user, sprint_id, write=True, permission="sprint.manage"
    )
    await sprints.start_sprint(db, sprint, sprints.SprintSpec(**body.model_dump()))
    return await sprint_out(db, principal, sprint)


@router.post("/sprints/{sprint_id}/complete", response_model=SprintCompleteOut)
async def complete_sprint(
    sprint_id: UUID, body: SprintComplete, principal: CurrentPrincipal, db: Db
) -> SprintCompleteOut:
    _, sprint = await sprints.load_sprint(
        db, principal.user, sprint_id, write=True, permission="sprint.manage"
    )
    result = await sprints.complete_sprint(
        db,
        principal.user,
        sprint,
        move_unfinished_to=body.move_unfinished_to,
        tag_backlog=body.tag_backlog,
    )
    return SprintCompleteOut(
        sprint=await sprint_out(db, principal, result.sprint),
        moved_to=await sprint_out(db, principal, result.moved_to) if result.moved_to else None,
        unfinished=result.unfinished,
    )


@router.post("/sprints/{sprint_id}/tickets", response_model=SprintKeysOut)
async def add_tickets(
    sprint_id: UUID, body: SprintKeys, principal: CurrentPrincipal, db: Db
) -> SprintKeysOut:
    """Takes them out of any other open sprint and removes #backlog."""
    _, sprint = await sprints.load_sprint(db, principal.user, sprint_id, permission="ticket.edit")
    return SprintKeysOut(keys=await sprints.add_tickets(db, principal.user, sprint, body.keys))


@router.delete("/sprints/{sprint_id}/tickets", response_model=SprintKeysOut)
async def remove_tickets(
    sprint_id: UUID, body: SprintKeys, principal: CurrentPrincipal, db: Db
) -> SprintKeysOut:
    _, sprint = await sprints.load_sprint(db, principal.user, sprint_id, permission="ticket.edit")
    return SprintKeysOut(keys=await sprints.remove_tickets(db, principal.user, sprint, body.keys))


@router.get("/sprints/{sprint_id}/report", response_model=SprintReport)
async def sprint_report(sprint_id: UUID, principal: CurrentPrincipal, db: Db) -> SprintReport:
    """Saved when the sprint closes; live while it is active."""
    _, sprint = await sprints.load_sprint(db, principal.user, sprint_id)
    data = await sprints.report(db, sprint)
    visible = {
        f"{key}-{number}"
        for key, number in await db.execute(
            search.base_query(principal.user).with_only_columns(Project.key, Ticket.number)
        )
    }
    return report_out(data, visible)


@router.get("/boards/{board_id}/backlog", response_model=BacklogOut)
async def board_backlog(
    board_id: UUID,
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    quick_filters: Annotated[list[UUID] | None, Query()] = None,
    q: str | None = Query(default=None, description="Extra RQL, combined with AND"),
) -> BacklogOut:
    """Tickets of the board's source in no open sprint and not done, by rank (first 500)."""
    ba = await boards.load_board(db, principal.user, board_id)
    parts = [f"({q})"] if q and q.strip() else []
    if quick_filters:
        rows = await db.scalars(
            select(BoardQuickFilter.rql).where(
                BoardQuickFilter.board_id == ba.board.id, BoardQuickFilter.id.in_(quick_filters)
            )
        )
        parts += [f"({rql})" for rql in rows]
    items, total = await sprints.backlog(
        db, principal.user, ba, extra=" AND ".join(parts), timezone=settings.timezone
    )
    return BacklogOut(items=await summaries_out(db, items), total=total)
