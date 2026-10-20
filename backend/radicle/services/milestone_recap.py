"""The numbers behind a finished milestone, for the celebration card people share."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Comment,
    Milestone,
    Project,
    Status,
    StatusCategory,
    Ticket,
    TicketType,
    User,
    UserKind,
    Worklog,
)

# Faces on the card; the count covers everyone.
MAX_PEOPLE = 8


@dataclass
class Recap:
    milestone: Milestone
    project: Project
    tickets: int = 0
    done: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    minutes_logged: int = 0
    comments: int = 0
    people: list[User] = field(default_factory=list)
    humans: int = 0
    agents: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def complete(self) -> bool:
        return self.tickets > 0 and self.done == self.tickets

    @property
    def days(self) -> int | None:
        if not (self.started_at and self.finished_at):
            return None
        return max(1, (self.finished_at - self.started_at).days)

    @property
    def on_time(self) -> bool | None:
        target = self.milestone.target_date
        if not (target and self.complete and self.finished_at):
            return None
        return self.finished_at.date() <= target


async def recap(db: AsyncSession, project: Project, milestone: Milestone) -> Recap:
    live = (Ticket.milestone_id == milestone.id) & Ticket.deleted_at.is_(None)
    out = Recap(milestone, project)

    rows = await db.execute(
        select(Ticket.type, Status.category, func.count())
        .join(Status, Status.id == Ticket.status_id)
        .where(live)
        .group_by(Ticket.type, Status.category)
    )
    for type_, category, count in rows.all():
        out.tickets += count
        out.by_type[TicketType(type_).value] = out.by_type.get(TicketType(type_).value, 0) + count
        if StatusCategory(category) is StatusCategory.done:
            out.done += count

    span = await db.execute(
        select(func.min(Ticket.created_at), func.max(Ticket.resolved_at)).where(live)
    )
    out.started_at, out.finished_at = span.one()

    ids = select(Ticket.id).where(live).scalar_subquery()
    out.minutes_logged = int(
        await db.scalar(
            select(func.coalesce(func.sum(Worklog.minutes), 0)).where(
                Worklog.ticket_id.in_(ids), Worklog.deleted_at.is_(None)
            )
        )
        or 0
    )
    out.comments = int(
        await db.scalar(
            select(func.count()).where(Comment.ticket_id.in_(ids), Comment.deleted_at.is_(None))
        )
        or 0
    )

    # Everyone who worked on it: assignees, reporters, commenters and people who logged time.
    involved = union(
        select(Ticket.assignee_id.label("id")).where(live, Ticket.assignee_id.is_not(None)),
        select(Ticket.reporter_id).where(live),
        select(Comment.author_id).where(Comment.ticket_id.in_(ids), Comment.deleted_at.is_(None)),
        select(Worklog.user_id).where(Worklog.ticket_id.in_(ids), Worklog.deleted_at.is_(None)),
    ).subquery()
    users = (
        await db.scalars(
            select(User)
            .where(User.id.in_(select(involved.c.id)), User.kind != UserKind.system)
            .order_by(User.display_name)
        )
    ).all()
    out.humans = sum(1 for u in users if u.kind is UserKind.human)
    out.agents = sum(1 for u in users if u.kind is UserKind.agent)
    out.people = list(users[:MAX_PEOPLE])
    return out
