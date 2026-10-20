from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from radicle.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.api.schemas.boards import (
    BoardCreate,
    BoardDataOut,
    BoardMoveIn,
    BoardMoveOut,
    BoardOut,
    BoardPatch,
    BoardStatus,
    Card,
    ColumnData,
    ColumnOut,
    LaneOut,
    QuickFilterIn,
    QuickFilterOut,
)
from radicle.api.schemas.common import Page
from radicle.api.schemas.tickets import WarningOut
from radicle.api.sprints import sprint_out
from radicle.api.ticket_views import summaries_out
from radicle.db.models import Board, BoardKind, Project, ProjectRole, Status, Swimlane
from radicle.services import boards, sprints
from radicle.services.access import project_access

router = APIRouter(tags=["boards"])
ADMIN = ProjectRole.admin


def _status(s: Status) -> BoardStatus:
    return BoardStatus(id=str(s.id), name=s.name, type=s.ticket_type, category=s.category)


async def board_out(db: Db, board: Board) -> BoardOut:
    statuses = await boards.scope_statuses(db, board)
    columns = boards.resolve_columns(board, statuses)
    mapped = set().union(*(c.status_ids for c in columns)) if columns else set()
    project = await db.get(Project, board.project_id) if board.project_id else None
    return BoardOut(
        id=str(board.id),
        project=project.key if project else None,
        name=board.name,
        kind=board.kind,
        source_rql=board.source_rql,
        columns=[ColumnOut(**c) for c in board.columns],
        wip_mode=board.wip_mode,
        swimlane_by=board.swimlane_by,
        card_fields=list(board.card_fields),
        done_window_days=board.done_window_days,
        quick_filters=[
            QuickFilterOut(id=str(q.id), name=q.name, rql=q.rql, position=q.position)
            for q in await boards.quick_filters(db, board)
        ],
        statuses=[_status(s) for s in statuses],
        unmapped_statuses=[_status(s) for s in statuses if s.id not in mapped],
        created_at=board.created_at,
        updated_at=board.updated_at,
    )


@router.get("/projects/{key}/boards", response_model=Page[BoardOut])
async def list_boards(key: str, principal: CurrentPrincipal, db: Db) -> Page[BoardOut]:
    access = await project_access(db, principal.user, key)
    return Page(
        items=[await board_out(db, b) for b in await boards.list_boards(db, access.project)]
    )


@router.post("/projects/{key}/boards", response_model=BoardOut, status_code=201)
async def create_board(
    key: str, body: BoardCreate, principal: CurrentPrincipal, db: Db
) -> BoardOut:
    access = await project_access(db, principal.user, key, write=True, permission="board.manage")
    board = await boards.create_board(
        db,
        access,
        boards.BoardSpec(
            name=body.name,
            kind=body.kind,
            source_rql=body.source_rql,
            columns=[c.model_dump(mode="json") for c in body.columns] if body.columns else None,
            wip_mode=body.wip_mode,
            swimlane_by=body.swimlane_by,
            card_fields=body.card_fields,
            done_window_days=body.done_window_days,
        ),
    )
    return await board_out(db, board)


@router.get("/boards/{board_id}", response_model=BoardOut)
async def get_board(board_id: UUID, principal: CurrentPrincipal, db: Db) -> BoardOut:
    ba = await boards.load_board(db, principal.user, board_id)
    return await board_out(db, ba.board)


@router.patch("/boards/{board_id}", response_model=BoardOut)
async def patch_board(
    board_id: UUID, body: BoardPatch, principal: CurrentPrincipal, db: Db
) -> BoardOut:
    """Columns group statuses (by id, or whole categories); a status sits in one column."""
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="board.manage"
    )
    changes = body.model_dump(mode="json", exclude_unset=True)
    await boards.update_board(db, ba.board, changes)
    return await board_out(db, ba.board)


@router.delete("/boards/{board_id}", status_code=204)
async def delete_board(board_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="board.manage"
    )
    await db.delete(ba.board)
    return Response(status_code=204)


@router.get("/boards/{board_id}/quick-filters", response_model=Page[QuickFilterOut])
async def list_quick_filters(
    board_id: UUID, principal: CurrentPrincipal, db: Db
) -> Page[QuickFilterOut]:
    ba = await boards.load_board(db, principal.user, board_id)
    return Page(
        items=[
            QuickFilterOut(id=str(q.id), name=q.name, rql=q.rql, position=q.position)
            for q in await boards.quick_filters(db, ba.board)
        ]
    )


@router.post("/boards/{board_id}/quick-filters", response_model=QuickFilterOut, status_code=201)
async def create_quick_filter(
    board_id: UUID, body: QuickFilterIn, principal: CurrentPrincipal, db: Db
) -> QuickFilterOut:
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="board.manage"
    )
    q = await boards.save_quick_filter(
        db, ba.board, name=body.name, rql=body.rql, position=body.position
    )
    return QuickFilterOut(id=str(q.id), name=q.name, rql=q.rql, position=q.position)


@router.patch("/boards/{board_id}/quick-filters/{filter_id}", response_model=QuickFilterOut)
async def patch_quick_filter(
    board_id: UUID, filter_id: UUID, body: QuickFilterIn, principal: CurrentPrincipal, db: Db
) -> QuickFilterOut:
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="board.manage"
    )
    existing = await boards.get_quick_filter(db, ba.board, filter_id)
    q = await boards.save_quick_filter(
        db, ba.board, name=body.name, rql=body.rql, position=body.position, existing=existing
    )
    return QuickFilterOut(id=str(q.id), name=q.name, rql=q.rql, position=q.position)


@router.delete("/boards/{board_id}/quick-filters/{filter_id}", status_code=204)
async def delete_quick_filter(
    board_id: UUID, filter_id: UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    ba = await boards.load_board(
        db, principal.user, board_id, write=True, permission="board.manage"
    )
    await db.delete(await boards.get_quick_filter(db, ba.board, filter_id))
    return Response(status_code=204)


@router.get("/boards/{board_id}/data", response_model=BoardDataOut)
async def board_data(
    board_id: UUID,
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    quick_filters: Annotated[list[UUID] | None, Query()] = None,
    swimlane: Swimlane | None = None,
    column: int | None = Query(default=None, description="Only this column (to page it)"),
    cursor: str | None = None,
    q: str | None = Query(default=None, description="Extra RQL, combined with AND"),
) -> BoardDataOut:
    """Cards grouped by column (50 per column, by rank), with WIP counts and lanes.
    Active quick filters combine with AND."""
    ba = await boards.load_board(db, principal.user, board_id)
    data = await boards.board_data(
        db,
        principal.user,
        ba.board,
        quick_filter_ids=quick_filters or [],
        swimlane=swimlane,
        only_column=column,
        cursor=cursor,
        timezone=settings.timezone,
        extra=q,
    )
    by = swimlane or ba.board.swimlane_by
    out_columns = []
    lane_counts: dict[tuple[str, str], int] = {}
    for c in data.columns:
        summaries = await summaries_out(db, c.tickets, principal.user)
        cards = []
        for ticket, summary in zip(c.tickets, summaries, strict=True):
            lane = data.lanes.get(ticket.id, boards.NO_LANE)
            lane_counts[lane] = lane_counts.get(lane, 0) + 1
            cards.append(Card(**summary.model_dump(), lane=lane[0]))
        out_columns.append(
            ColumnData(
                index=c.index,
                name=c.name,
                wip_limit=c.wip_limit,
                count=c.total,
                over_limit=c.over_limit,
                done_only=c.done_only,
                tickets=cards,
                next_cursor=c.next_cursor,
            )
        )
    lanes = (
        [
            LaneOut(key=key, label=label, count=lane_counts[(key, label)])
            for key, label in boards.lane_order(by, list(lane_counts))
        ]
        if by is not Swimlane.none
        else []
    )
    active = await sprints.active_sprint(db, ba.board) if ba.board.kind is BoardKind.scrum else None
    return BoardDataOut(
        board=await board_out(db, ba.board),
        swimlane_by=by,
        lanes=lanes,
        columns=out_columns,
        sprint=await sprint_out(db, principal, active) if active else None,
    )


@router.post("/boards/{board_id}/move", response_model=BoardMoveOut)
async def move_card(
    board_id: UUID, body: BoardMoveIn, principal: CurrentPrincipal, db: Db, settings: AppSettings
) -> BoardMoveOut:
    """Transition into the column (when it changes) and rank, in one call."""
    ba = await boards.load_board(db, principal.user, board_id)
    result = await boards.move(
        db,
        principal.user,
        ba,
        key=body.ticket,
        column=body.column,
        before=body.before,
        after=body.after,
        transition=body.transition,
        resolution=body.resolution,
        comment=body.comment,
        fields=body.fields,
        log_minutes=body.log_minutes,
        force=body.force,
        timezone=settings.timezone,
    )
    summary = (await summaries_out(db, [result.ticket], principal.user))[0]
    return BoardMoveOut(
        ticket=summary,
        warnings=[WarningOut(code=w.code, message=w.message, by=w.by) for w in result.warnings],
    )
