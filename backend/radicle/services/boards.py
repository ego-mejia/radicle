"""Configurable boards: columns of statuses, WIP limits, swimlanes and quick filters."""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.db.models import (
    PRIORITY_ORDER,
    Area,
    Board,
    BoardKind,
    BoardQuickFilter,
    Milestone,
    Project,
    ProjectRole,
    Sprint,
    SprintState,
    SprintTicket,
    Status,
    StatusCategory,
    Swimlane,
    Ticket,
    User,
    WipMode,
    utcnow,
)
from radicle.query.errors import RQLError
from radicle.query.parser import parse
from radicle.services import ranking, search, tickets, transitions
from radicle.services.access import ProjectAccess, project_access

NAME_MAX = 80
COLUMNS_MAX = 12
PAGE = 50
CARD_FIELDS = (
    "priority",
    "assignee",
    "tags",
    "due",
    "estimate",
    "remaining",
    "checklist",
    "votes",
)
MAIN_COLUMNS: list[dict[str, Any]] = [
    {"name": "To Do", "categories": ["todo"], "status_ids": [], "wip_limit": None},
    {"name": "In Progress", "categories": ["in_progress"], "status_ids": [], "wip_limit": None},
    {"name": "Done", "categories": ["done"], "status_ids": [], "wip_limit": None},
]
DEFAULT_QUICK_FILTERS = (
    ("My tickets", "assignee = currentUser()"),
    ("Only bugs", "type = bug"),
    ("#backlog", "#backlog"),
    ("Blocked", "blocked = true"),
)


def _fail(field_name: str, detail: str) -> ValidationFailed:
    return ValidationFailed(detail, errors=[{"field": field_name, "message": "invalid"}])


def _not_found(board_id: object) -> NotFound:
    return NotFound(f"Board {board_id} not found.", code="board_not_found")


# --- access --------------------------------------------------------------------------------


@dataclass(frozen=True)
class BoardAccess:
    board: Board
    role: ProjectRole
    project: Project | None


async def load_board(
    db: AsyncSession,
    user: User,
    board_id: uuid.UUID,
    *,
    need: ProjectRole = ProjectRole.viewer,
    write: bool = False,
    permission: str | None = None,
) -> BoardAccess:
    board = await db.get(Board, board_id)
    if board is None:
        raise _not_found(board_id)
    if board.project_id is None:
        # Multi-project boards: anyone can look (tickets are filtered per user);
        # only instance admins change them.
        role = ProjectRole.admin if user.is_instance_admin else ProjectRole.viewer
        changes = need is not ProjectRole.viewer or permission is not None
        if changes and role is not ProjectRole.admin:
            raise Forbidden("Only instance admins change boards that span several projects.")
        return BoardAccess(board, role, None)
    project = await db.get(Project, board.project_id)
    if project is None:  # pragma: no cover - foreign key
        raise _not_found(board_id)
    try:
        access = await project_access(
            db, user, project.key, need=need, write=write, permission=permission
        )
    except NotFound:
        raise _not_found(board_id) from None
    return BoardAccess(board, access.role, project)


async def list_boards(db: AsyncSession, project: Project) -> list[Board]:
    return list(
        await db.scalars(
            select(Board).where(Board.project_id == project.id).order_by(Board.created_at)
        )
    )


# --- config --------------------------------------------------------------------------------


async def scope_statuses(db: AsyncSession, board: Board) -> list[Status]:
    query = select(Status)
    if board.project_id is not None:
        query = query.where(Status.project_id == board.project_id)
    return list(await db.scalars(query.order_by(Status.ticket_type, Status.position)))


def check_columns(raw: list[dict[str, Any]], statuses: list[Status]) -> list[dict[str, Any]]:
    if not raw:
        raise _fail("columns", "A board needs at least one column.")
    if len(raw) > COLUMNS_MAX:
        raise _fail("columns", f"A board can have at most {COLUMNS_MAX} columns.")
    known = {str(s.id) for s in statuses}
    seen_names: set[str] = set()
    seen_status: set[str] = set()
    out = []
    for column in raw:
        name = " ".join(str(column.get("name", "")).split())
        if not 1 <= len(name) <= NAME_MAX or name.lower() in seen_names:
            raise _fail("columns", f"Column names must be unique and 1 to {NAME_MAX} characters.")
        seen_names.add(name.lower())
        ids = [str(i) for i in column.get("status_ids") or []]
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise _fail("columns", f"Column '{name}' has statuses that are not in this board.")
        repeated = [i for i in ids if i in seen_status]
        if repeated:
            raise _fail("columns", f"A status can only be in one column (see '{name}').")
        seen_status.update(ids)
        categories = [str(c) for c in column.get("categories") or []]
        if any(c not in StatusCategory.__members__ for c in categories):
            raise _fail("columns", "Categories are todo, in_progress or done.")
        limit = column.get("wip_limit")
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise _fail("columns", f"WIP limit of '{name}' must be a positive number or empty.")
        out.append({"name": name, "status_ids": ids, "categories": categories, "wip_limit": limit})
    return out


def _check_rql(rql: str, path: str = "source_rql") -> str:
    try:
        parse(rql)
    except RQLError as exc:
        raise _fail(path, f"The query is not valid RQL: {exc.detail}") from None
    return rql.strip()


def _check_card_fields(fields: list[str]) -> list[str]:
    bad = [f for f in fields if f not in CARD_FIELDS and not f.startswith("cf.")]
    if bad:
        raise _fail("card_fields", f"Unknown card fields: {', '.join(bad)}.")
    return list(dict.fromkeys(fields))


async def create_default_board(db: AsyncSession, project: Project, user: User | None) -> Board:
    board = Board(
        project_id=project.id,
        name="Main",
        kind=BoardKind.kanban,
        source_rql=f"project = {project.key}",
        columns=[dict(c) for c in MAIN_COLUMNS],
        wip_mode=WipMode.soft,
        swimlane_by=Swimlane.none,
        card_fields=["priority", "assignee", "tags", "checklist"],
        done_window_days=14,
        created_by=user.id if user else None,
    )
    db.add(board)
    await db.flush()
    for position, (name, rql) in enumerate(DEFAULT_QUICK_FILTERS):
        db.add(BoardQuickFilter(board_id=board.id, name=name, rql=rql, position=position))
    await db.flush()
    return board


@dataclass
class BoardSpec:
    name: str
    kind: BoardKind = BoardKind.kanban
    source_rql: str | None = None
    columns: list[dict[str, Any]] | None = None
    wip_mode: WipMode = WipMode.soft
    swimlane_by: Swimlane = Swimlane.none
    card_fields: list[str] = field(default_factory=lambda: ["priority", "assignee", "tags"])
    done_window_days: int = 14


def _name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= NAME_MAX:
        raise _fail("name", f"Board names are 1 to {NAME_MAX} characters.")
    return name


def _window(days: int) -> int:
    if not 1 <= days <= 365:
        raise _fail("done_window_days", "done_window_days must be between 1 and 365.")
    return days


async def create_board(db: AsyncSession, access: ProjectAccess, spec: BoardSpec) -> Board:
    board = Board(
        project_id=access.project.id,
        name=_name(spec.name),
        kind=spec.kind,
        source_rql=_check_rql(spec.source_rql or f"project = {access.project.key}"),
        columns=[],
        wip_mode=spec.wip_mode,
        swimlane_by=spec.swimlane_by,
        card_fields=_check_card_fields(spec.card_fields),
        done_window_days=_window(spec.done_window_days),
        created_by=access.user.id,
    )
    statuses = await scope_statuses(db, board)
    board.columns = check_columns(spec.columns or [dict(c) for c in MAIN_COLUMNS], statuses)
    db.add(board)
    await db.flush()
    for position, (name, rql) in enumerate(DEFAULT_QUICK_FILTERS):
        db.add(BoardQuickFilter(board_id=board.id, name=name, rql=rql, position=position))
    await db.flush()
    return board


async def update_board(db: AsyncSession, board: Board, changes: dict[str, Any]) -> Board:
    if "name" in changes:
        board.name = _name(changes["name"])
    if "kind" in changes:
        board.kind = BoardKind(changes["kind"])
    if "source_rql" in changes:
        board.source_rql = _check_rql(changes["source_rql"])
    if "wip_mode" in changes:
        board.wip_mode = WipMode(changes["wip_mode"])
    if "swimlane_by" in changes:
        board.swimlane_by = Swimlane(changes["swimlane_by"])
    if "card_fields" in changes:
        board.card_fields = _check_card_fields(changes["card_fields"])
    if "done_window_days" in changes:
        board.done_window_days = _window(int(changes["done_window_days"]))
    if "columns" in changes:
        board.columns = check_columns(changes["columns"], await scope_statuses(db, board))
    board.updated_at = utcnow()
    await db.flush()
    return board


async def quick_filters(db: AsyncSession, board: Board) -> list[BoardQuickFilter]:
    return list(
        await db.scalars(
            select(BoardQuickFilter)
            .where(BoardQuickFilter.board_id == board.id)
            .order_by(BoardQuickFilter.position, BoardQuickFilter.name)
        )
    )


async def save_quick_filter(
    db: AsyncSession,
    board: Board,
    *,
    name: str,
    rql: str,
    position: int | None = None,
    existing: BoardQuickFilter | None = None,
) -> BoardQuickFilter:
    row = existing or BoardQuickFilter(board_id=board.id)
    row.name = _name(name)
    row.rql = _check_rql(rql, "rql")
    if position is not None:
        row.position = position
    elif existing is None:
        row.position = len(await quick_filters(db, board))
    if existing is None:
        db.add(row)
    await db.flush()
    return row


async def get_quick_filter(
    db: AsyncSession, board: Board, filter_id: uuid.UUID
) -> BoardQuickFilter:
    row = await db.get(BoardQuickFilter, filter_id)
    if row is None or row.board_id != board.id:
        raise NotFound(f"Quick filter {filter_id} not found.", code="quick_filter_not_found")
    return row


# --- data ----------------------------------------------------------------------------------


@dataclass
class Column:
    index: int
    name: str
    status_ids: set[uuid.UUID]  # explicit statuses plus those of its categories in scope
    wip_limit: int | None
    done_only: bool
    categories: set[StatusCategory] = field(default_factory=set)
    # A status sits in the first column that holds it: what earlier columns took.
    taken_ids: set[uuid.UUID] = field(default_factory=set)
    taken_categories: set[StatusCategory] = field(default_factory=set)

    def holds(self, status: Status) -> bool:
        if status.id in self.taken_ids or status.category in self.taken_categories:
            return False
        return status.id in self.status_ids or status.category in self.categories

    tickets: list[Ticket] = field(default_factory=list)
    total: int = 0
    next_cursor: str | None = None

    @property
    def over_limit(self) -> bool:
        return self.wip_limit is not None and self.total > self.wip_limit


@dataclass
class BoardData:
    board: Board
    columns: list[Column]
    unmapped: list[Status]
    lanes: dict[uuid.UUID, tuple[str, str]]  # ticket id -> (lane key, lane label)


def resolve_columns(board: Board, statuses: list[Status]) -> list[Column]:
    columns = []
    taken_ids: set[uuid.UUID] = set()
    taken_categories: set[StatusCategory] = set()
    for index, raw in enumerate(board.columns):
        categories = {StatusCategory(c) for c in raw.get("categories") or []}
        ids = {uuid.UUID(i) for i in raw.get("status_ids") or []}
        ids |= {s.id for s in statuses if s.category in categories}
        ids = {
            i
            for i in ids
            if i not in taken_ids
            and not any(s.id == i and s.category in taken_categories for s in statuses)
        }
        in_column = [s for s in statuses if s.id in ids]
        done_only = bool(in_column) and all(s.category is StatusCategory.done for s in in_column)
        columns.append(
            Column(
                index,
                raw["name"],
                ids,
                raw.get("wip_limit"),
                done_only,
                categories - taken_categories,
                set(taken_ids),
                set(taken_categories),
            )
        )
        taken_ids |= ids
        taken_categories |= categories
    return columns


async def _base_where(
    db: AsyncSession,
    user: User,
    board: Board,
    quick_filter_ids: list[uuid.UUID],
    timezone: str,
    extra: str | None = None,
) -> ColumnElement[bool]:
    parts = [f"({board.source_rql})"] if board.source_rql.strip() else []
    if extra and extra.strip():
        parts.append(f"({extra})")
    if quick_filter_ids:
        rows = await db.scalars(
            select(BoardQuickFilter.rql).where(
                BoardQuickFilter.board_id == board.id, BoardQuickFilter.id.in_(quick_filter_ids)
            )
        )
        parts += [f"({rql})" for rql in rows]
    compiled = await search.compile_rql(db, user, " AND ".join(parts), timezone=timezone)
    return compiled.where


def _column_where(column: Column, window_days: int | None) -> ColumnElement[bool]:
    # Categories match statuses of any project the source reaches, not only this one's.
    by_category: ColumnElement[bool] = (
        Status.category.in_(column.categories) if column.categories else false()
    )
    if column.categories and column.taken_ids:
        by_category = and_(by_category, Ticket.status_id.not_in(column.taken_ids))
    where: ColumnElement[bool] = or_(
        Ticket.status_id.in_(column.status_ids) if column.status_ids else false(),
        by_category,
    )
    if column.done_only and window_days is not None:
        since = utcnow() - timedelta(days=window_days)
        where = and_(where, Ticket.resolved_at >= since)
    return where


def _active_sprint_tickets(board: Board) -> Select[Any]:
    return (
        select(SprintTicket.ticket_id)
        .join(Sprint, Sprint.id == SprintTicket.sprint_id)
        .where(
            Sprint.board_id == board.id,
            Sprint.state == SprintState.active,
            SprintTicket.removed_at.is_(None),
        )
    )


async def board_data(
    db: AsyncSession,
    user: User,
    board: Board,
    *,
    quick_filter_ids: list[uuid.UUID] | None = None,
    swimlane: Swimlane | None = None,
    only_column: int | None = None,
    cursor: str | None = None,
    timezone: str = "UTC",
    extra: str | None = None,
) -> BoardData:
    """Tickets the user can see, grouped by column (first 50 each, by rank)."""
    statuses = await scope_statuses(db, board)
    columns = resolve_columns(board, statuses)
    mapped = set().union(*(c.status_ids for c in columns)) if columns else set()
    base = await _base_where(db, user, board, quick_filter_ids or [], timezone, extra)
    window: int | None = board.done_window_days
    if board.kind is BoardKind.scrum:
        # A Scrum board shows the active sprint, done tickets included.
        base = and_(base, Ticket.id.in_(_active_sprint_tickets(board)))
        window = None
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    for column in columns:
        if only_column is not None and column.index != only_column:
            continue
        query = search.base_query(user).where(base, _column_where(column, window))
        column.total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        rows = list(
            await db.scalars(query.order_by(Ticket.rank, Ticket.id).offset(offset).limit(PAGE + 1))
        )
        column.tickets = rows[:PAGE]
        column.next_cursor = str(offset + PAGE) if len(rows) > PAGE else None
    if only_column is not None:
        columns = [c for c in columns if c.index == only_column]
    lanes = await _lanes(db, swimlane or board.swimlane_by, [t for c in columns for t in c.tickets])
    unmapped = [s for s in statuses if s.id not in mapped]
    return BoardData(board, columns, unmapped, lanes)


NO_LANE = ("", "")


async def _lanes(
    db: AsyncSession, by: Swimlane, items: list[Ticket]
) -> dict[uuid.UUID, tuple[str, str]]:
    if by is Swimlane.none or not items:
        return {}
    if by is Swimlane.priority:
        return {t.id: (str(PRIORITY_ORDER[t.priority]), t.priority.value) for t in items}
    if by is Swimlane.type:
        return {t.id: (t.type.value, t.type.value) for t in items}
    if by is Swimlane.assignee:
        return {
            t.id: (t.assignee.handle, t.assignee.handle) if t.assignee else NO_LANE for t in items
        }
    ids = {getattr(t, f"{by.value}_id") for t in items} - {None}
    labels: dict[uuid.UUID, str] = {}
    if by is Swimlane.area and ids:
        labels = dict((await db.execute(select(Area.id, Area.name).where(Area.id.in_(ids)))).all())
    elif by is Swimlane.milestone and ids:
        labels = dict(
            (
                await db.execute(select(Milestone.id, Milestone.name).where(Milestone.id.in_(ids)))
            ).all()
        )
    elif by is Swimlane.parent and ids:
        rows = await db.execute(
            select(Ticket.id, Project.key, Ticket.number, Ticket.title)
            .join(Project, Project.id == Ticket.project_id)
            .where(Ticket.id.in_(ids))
        )
        labels = {tid: f"{key}-{number} {title}" for tid, key, number, title in rows.all()}
    result = {}
    for t in items:
        value = getattr(t, f"{by.value}_id")
        result[t.id] = (str(value), labels.get(value, "?")) if value else NO_LANE
    return result


# --- move ----------------------------------------------------------------------------------


@dataclass
class MoveResult:
    ticket: Ticket
    warnings: list[transitions.TicketWarning]


async def move(
    db: AsyncSession,
    user: User,
    ba: BoardAccess,
    *,
    key: str,
    column: int,
    before: str | None = None,
    after: str | None = None,
    transition: str | None = None,
    resolution: Any = None,
    comment: str | None = None,
    fields: dict[str, Any] | None = None,
    log_minutes: int | None = None,
    force: bool = False,
    timezone: str = "UTC",
) -> MoveResult:
    """Move a card to a column (transition) and/or within it (rank)."""
    access, ticket = await tickets.load_ticket(db, user, key, write=True)
    board = ba.board
    statuses = await scope_statuses(db, board)
    columns = resolve_columns(board, statuses)
    if not 0 <= column < len(columns):
        raise _fail("column", f"Column {column} does not exist; the board has {len(columns)}.")
    target = columns[column]
    warnings: list[transitions.TicketWarning] = []
    access.require("ticket.edit" if target.holds(ticket.status) else "ticket.transition")
    if not target.holds(ticket.status):
        note: dict[str, Any] = {}
        if target.wip_limit is not None and board.wip_mode is WipMode.hard:
            base = await _base_where(db, user, board, [], timezone)
            count = await db.scalar(
                select(func.count()).select_from(
                    search.base_query(user)
                    .where(base, _column_where(target, board.done_window_days))
                    .subquery()
                )
            )
            if (count or 0) >= target.wip_limit:
                if not (force and access.at_least(ProjectRole.admin)):
                    raise Conflict(
                        f"'{target.name}' is at its WIP limit ({target.wip_limit}). Finish "
                        "something there first"
                        + (
                            ", or force it as admin." if access.at_least(ProjectRole.admin) else "."
                        ),
                        code="wip_limit_reached",
                        extra={
                            "wip_limit": target.wip_limit,
                            "count": int(count or 0),
                            "can_force": access.at_least(ProjectRole.admin),
                        },
                    )
                note["wip_forced"] = target.name
        options = [
            v.option
            for v in await transitions.transition_options(db, access, ticket)
            if v.available and target.holds(v.option.to_status)
        ]
        if transition:
            options = [o for o in options if o.transition.name.lower() == transition.lower()]
        if not options:
            raise Conflict(
                f"{access.project.key}-{ticket.number} cannot move to '{target.name}': no "
                "transition from its status leads there.",
                code="column_rejects",
            )
        if len({(o.transition.name, o.to_status.id) for o in options}) > 1:
            raise Conflict(
                f"Several transitions lead to '{target.name}'; pick one.",
                code="choose_transition",
                extra={
                    "options": [
                        {"name": o.transition.name, "to_status": o.to_status.name} for o in options
                    ]
                },
            )
        chosen = options[0]
        warnings = await transitions.transition_ticket(
            db,
            access,
            ticket,
            to_status=chosen.to_status.name,
            transition=chosen.transition.name,
            resolution=resolution,
            comment=comment,
            fields=fields,
            log_minutes=log_minutes,
            force=force,
            note=note,
        )
    if before or after:
        await ranking.rank_ticket(db, access, ticket, before=before, after=after)
    return MoveResult(ticket, warnings)


def lane_order(by: Swimlane, lanes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    unique = list(dict.fromkeys(lanes))
    named = [lane for lane in unique if lane != NO_LANE]
    if by is Swimlane.priority:
        named.sort(key=lambda lane: -int(lane[0]))
    else:
        named.sort(key=lambda lane: lane[1].lower())
    return named + ([NO_LANE] if NO_LANE in unique else [])
