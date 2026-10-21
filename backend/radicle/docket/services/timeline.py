"""Timeline (Gantt) data: tickets with dates grouped by milestone or area, plus Blocks arrows."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Area, LinkType, Milestone, Project, Ticket, TicketLink, User
from radicle.docket.services import forecast, search

GroupBy = Literal["milestone", "area"]
LIMIT = 2000
NO_GROUP = ""


@dataclass
class Group:
    key: str
    label: str
    milestone: Milestone | None = None
    progress: forecast.Progress | None = None
    tickets: list[Ticket] = field(default_factory=list)


@dataclass(frozen=True)
class Dependency:
    blocker: uuid.UUID
    blocked: uuid.UUID
    conflict: bool


@dataclass
class Timeline:
    groups: list[Group]
    undated: list[Ticket]
    dependencies: list[Dependency]
    truncated: bool


def _end(t: Ticket) -> date | None:
    return t.due_date or t.start_date


def _begin(t: Ticket) -> date | None:
    return t.start_date or t.due_date


async def timeline(
    db: AsyncSession,
    user: User,
    project: Project,
    *,
    group_by: GroupBy = "milestone",
    q: str | None = None,
    start: date | None = None,
    end: date | None = None,
    today: date,
    timezone: str = "UTC",
) -> Timeline:
    """Tickets with a start or due date inside [start, end] (when given), grouped; tickets
    without dates go to `undated`. Arrows go from blocker to blocked; a conflict is a blocker
    that ends after the blocked ticket begins."""
    rql = f"project = {project.key}" + (f" AND ({q})" if q and q.strip() else "")
    compiled = await search.compile_rql(db, user, rql, timezone=timezone)
    query = search.base_query(user).where(compiled.where)
    if start is not None:
        query = query.where(
            or_(
                and_(Ticket.start_date.is_(None), Ticket.due_date.is_(None)),
                Ticket.due_date >= start,
                and_(Ticket.due_date.is_(None), Ticket.start_date >= start),
            )
        )
    if end is not None:
        query = query.where(
            or_(
                and_(Ticket.start_date.is_(None), Ticket.due_date.is_(None)),
                Ticket.start_date <= end,
                and_(Ticket.start_date.is_(None), Ticket.due_date <= end),
            )
        )
    rows = list(
        await db.scalars(
            query.order_by(
                Ticket.start_date.asc().nulls_last(),
                Ticket.due_date.asc().nulls_last(),
                Ticket.rank,
                Ticket.id,
            ).limit(LIMIT + 1)
        )
    )
    truncated = len(rows) > LIMIT
    rows = rows[:LIMIT]

    groups: dict[str, Group] = {}
    if group_by == "milestone":
        for m in await forecast.project_milestones(db, project.id):
            progress = await forecast.milestone_progress(db, user, m, today=today)
            groups[str(m.id)] = Group(str(m.id), m.name, m, progress)
        names: dict[uuid.UUID, str] = {}
    else:
        areas = await db.scalars(
            select(Area).where(Area.project_id == project.id).order_by(Area.position, Area.name)
        )
        names = {a.id: a.name for a in areas}
        for area_id, name in names.items():
            groups[str(area_id)] = Group(str(area_id), name)
    groups[NO_GROUP] = Group(NO_GROUP, "")

    undated: list[Ticket] = []
    for t in rows:
        if t.start_date is None and t.due_date is None:
            undated.append(t)
            continue
        ref = t.milestone_id if group_by == "milestone" else t.area_id
        key = str(ref) if ref is not None and str(ref) in groups else NO_GROUP
        groups[key].tickets.append(t)

    dated = {t.id: t for g in groups.values() for t in g.tickets}
    dependencies: list[Dependency] = []
    if dated:
        links = await db.execute(
            select(TicketLink.source_id, TicketLink.target_id).where(
                TicketLink.type == LinkType.blocks,
                TicketLink.source_id.in_(dated),
                TicketLink.target_id.in_(dated),
            )
        )
        for blocker_id, blocked_id in links:
            blocker, blocked = dated[blocker_id], dated[blocked_id]
            finish, begin = _end(blocker), _begin(blocked)
            conflict = finish is not None and begin is not None and finish > begin
            dependencies.append(Dependency(blocker_id, blocked_id, conflict))

    ordered = [g for k, g in groups.items() if k != NO_GROUP]
    if group_by == "milestone":
        ordered = [g for g in ordered if g.tickets or (g.milestone and g.milestone.target_date)]
    else:
        ordered = [g for g in ordered if g.tickets]
    if groups[NO_GROUP].tickets:
        ordered.append(groups[NO_GROUP])
    return Timeline(ordered, undated, dependencies, truncated)
