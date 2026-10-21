"""Realistic demo and benchmark data. Used by scripts/seed.py and the performance test."""

import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    Area,
    Classification,
    LinkType,
    Milestone,
    Origin,
    Priority,
    Project,
    ProjectMember,
    ProjectRole,
    Resolution,
    Status,
    StatusCategory,
    Ticket,
    TicketEvent,
    TicketLink,
    TicketType,
    User,
    UserKind,
    utcnow,
)
from radicle.docket.services import periods, rank
from radicle.docket.services.templates import instantiate
from radicle.platform import security

AREAS = ["Legal", "Marketing", "Backend", "Frontend", "Mobile", "Data", "Infra", "Design"]
THINGS = [
    "checkout flow",
    "login page",
    "invoice export",
    "search results",
    "payment webhooks",
    "push notifications",
    "profile settings",
    "cart totals",
    "password reset",
    "CSV import",
    "order history",
    "shipping rates",
    "coupon codes",
    "onboarding emails",
    "admin reports",
    "product images",
    "session tokens",
    "inventory sync",
    "refunds",
    "two-factor login",
    "pricing page",
    "user permissions",
    "API rate limits",
    "calendar view",
    "file uploads",
]
TASK_TITLES = [
    "Add pagination to {t}",
    "Improve loading time of {t}",
    "Refactor {t} module",
    "Add tests for {t}",
    "Redesign {t}",
    "Support dark mode in {t}",
    "Track metrics for {t}",
    "Document {t}",
    "Translate {t} to Spanish",
    "Cache {t}",
]
BUG_TITLES = [
    "{T}: crash on Safari",
    "{T}: wrong totals",
    "{T}: timeout under load",
    "{T}: ignores the user's timezone",
    "Typo in {t}",
    "{T}: breaks with long names",
    "{T}: duplicate entries",
    "{T}: fails after the session expires",
]
DRAFT_TITLES = [
    "Idea: {t} on mobile",
    "Make {t} faster",
    "Simplify {t}",
    "Show {t} in the weekly email",
    "A/B test a new {t}",
]
DESCRIPTION = (
    "Customers reported this while using the {t}. Steps, expected behavior and screenshots "
    "are in the linked conversation.\n\n- [x] Reproduce it\n- [ ] Ship the fix"
)
TAGS = ["backlog", "payments", "ux", "tech-debt", "security", "perf", "mobile", "copy", "infra"]


def _dates(rng: random.Random, created: datetime) -> tuple[date | None, date | None]:
    """A due date for 40% of tickets; most of those also get a start, so the timeline
    has real bars."""
    if rng.random() >= 0.4:
        return None, None
    due = (created + timedelta(days=rng.randint(1, 90))).date()
    if rng.random() >= 0.75:
        return due, None
    start = max(created.date(), due - timedelta(days=rng.randint(2, 21)))
    return due, start


def _title(rng: random.Random, ticket_type: TicketType) -> tuple[str, str]:
    thing = rng.choice(THINGS)
    pool = {TicketType.bug: BUG_TITLES, TicketType.draft: DRAFT_TITLES}.get(
        ticket_type, TASK_TITLES
    )
    title = rng.choice(pool).format(t=thing, T=thing[0].upper() + thing[1:])
    return title, DESCRIPTION.format(t=thing)


HUMANS = ["fernando", "ana", "luis", "vera", "marta", "jorge"]
AGENTS = ["agent-backend", "agent-frontend", "agent-qa"]


def _inbox_fields(rng: random.Random) -> dict[str, object]:
    """Drafts land in the inbox: classified, half from users, most of them scored."""
    scored = rng.random() < 0.7
    origin = Origin.user if rng.random() < 0.5 else Origin.team
    kinds = [
        c for c in Classification if origin is Origin.team or c is not Classification.experiment
    ]
    return {
        "classification": rng.choice(kinds),
        "origin": origin,
        "impact": rng.randint(1, 5) if scored else None,
        "effort": rng.randint(1, 5) if scored else None,
    }


@dataclass(frozen=True)
class Seeded:
    project_key: str
    admin_email: str
    admin_password: str
    tickets: int


async def seed(
    db: AsyncSession,
    *,
    tickets: int,
    project_key: str = "PERF",
    password: str = "radicle-demo",  # noqa: S107 - documented demo password
    rng_seed: int = 7,
) -> Seeded:
    rng = random.Random(rng_seed)  # noqa: S311 - demo data, not security
    password_hash = security.hash_password(password)
    users: list[User] = []
    for handle in HUMANS:
        existing = await db.scalar(select(User).where(User.handle == handle))
        users.append(
            existing
            or User(
                handle=handle,
                display_name=handle.title(),
                email=f"{handle}@example.com",
                kind=UserKind.human,
                password_hash=password_hash,
                is_instance_admin=handle == "fernando",
            )
        )
    for handle in AGENTS:
        existing = await db.scalar(select(User).where(User.handle == handle))
        users.append(existing or User(handle=handle, display_name=handle, kind=UserKind.agent))
    db.add_all(users)
    await db.flush()

    project = Project(
        key=project_key,
        name="Acme Store" if project_key == "PA" else f"Project {project_key}",
        created_by=users[0].id,
    )
    db.add(project)
    await db.flush()
    await instantiate(db, project, users[0], template_id=None)
    from radicle.docket.services.boards import create_default_board

    await create_default_board(db, project, users[0])
    from radicle.docket.services.dashboards import create_project_summary

    await create_project_summary(db, project)
    for i, user in enumerate(users):
        role = (
            ProjectRole.admin
            if i == 0
            else (ProjectRole.viewer if user.handle == "vera" else ProjectRole.member)
        )
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
    areas = [Area(project_id=project.id, name=n, position=i) for i, n in enumerate(AREAS)]
    milestones = [
        Milestone(
            project_id=project.id,
            name=f"V{i + 1}",
            position=i,
            target_date=(utcnow() + timedelta(days=30 * (i + 1))).date(),
        )
        for i in range(4)
    ]
    db.add_all([*areas, *milestones])
    await db.flush()

    statuses = list(await db.scalars(select(Status).where(Status.project_id == project.id)))
    by_type = {t: [s for s in statuses if s.ticket_type is t] for t in TicketType}
    assignable = [u for u in users if u.handle != "vera"]
    now = utcnow()
    rows, events, ids = [], [], []
    current_rank: str | None = None
    for number in range(1, tickets + 1):
        ticket_type = rng.choices(list(TicketType), weights=[6, 3, 1])[0]
        status = rng.choice(by_type[ticket_type])
        done = status.category is StatusCategory.done
        created = now - timedelta(minutes=rng.randint(60 * 24 * 3, 60 * 24 * 180))
        # Done tickets were resolved a few days later; in-progress ones started after a while.
        resolved = created + timedelta(hours=rng.randint(4, 24 * 20)) if done else None
        current_rank = rank.after(current_rank)
        ticket_id = uuid.uuid4()
        ids.append(ticket_id)
        reporter = rng.choice(assignable)
        title, description = _title(rng, ticket_type)
        due_day, start_day = _dates(rng, created)
        rows.append(
            {
                "id": ticket_id,
                "project_id": project.id,
                "number": number,
                "type": ticket_type,
                "title": title,
                "description_md": description,
                "status_id": status.id,
                "resolution": (
                    Resolution.wont_do
                    if status.name == "Discarded"
                    else Resolution.done
                    if done
                    else None
                ),
                "priority": rng.choice(list(Priority)),
                "area_id": None if ticket_type is TicketType.draft else rng.choice(areas).id,
                "milestone_id": rng.choice(milestones).id if rng.random() < 0.6 else None,
                "assignee_id": rng.choice(assignable).id if rng.random() < 0.7 else None,
                "reporter_id": reporter.id,
                "due_date": due_day,
                "start_date": start_day,
                "estimate_hours": rng.choice([None, 1, 2, 3, 5, 8, 13]),
                "tags": rng.sample(TAGS, rng.randint(0, 3)),
                "rank": current_rank,
                "created_at": created,
                "updated_at": created + timedelta(hours=rng.randint(0, 200)),
                "resolved_at": resolved,
                **(_inbox_fields(rng) if ticket_type is TicketType.draft else {}),
            }
        )
        initial = next((s for s in by_type[ticket_type] if s.is_initial), by_type[ticket_type][0])
        events.append(
            {
                "ticket_id": ticket_id,
                "actor_id": reporter.id,
                "event_type": "created",
                "field": None,
                "old_value": None,
                "new_value": {"type": ticket_type.value, "status": initial.name},
                "created_at": created,
            }
        )
        # A believable path to the current status, so periods and reports have history.
        path: list[tuple[datetime, Status]] = []
        doing = [s for s in by_type[ticket_type] if s.category is StatusCategory.in_progress]
        if status.id != initial.id:
            if status.category is StatusCategory.done and resolved is not None:
                if doing and status.name != "Discarded":
                    started = created + (resolved - created) * rng.uniform(0.1, 0.6)
                    path.append((started, rng.choice(doing)))
                path.append((resolved, status))
            else:
                path.append((created + timedelta(hours=rng.randint(1, 72)), status))
        previous = initial
        for moment, step in path:
            events.append(
                {
                    "ticket_id": ticket_id,
                    "actor_id": reporter.id,
                    "event_type": "status_changed",
                    "field": "status",
                    "old_value": {"status": previous.name, "resolution": None},
                    "new_value": {"status": step.name},
                    "created_at": moment,
                }
            )
            previous = step
    for start in range(0, len(rows), 2000):
        await db.execute(insert(Ticket), rows[start : start + 2000])
        await db.execute(insert(TicketEvent), events[start : start + 2000])
    links = {(rng.choice(ids), rng.choice(ids)) for _ in range(max(1, tickets // 20))}
    link_rows = [
        {
            "id": uuid.uuid4(),
            "source_id": a,
            "target_id": b,
            "type": LinkType.blocks,
            "created_by": users[0].id,
        }
        for a, b in links
        if a != b
    ]
    if link_rows:
        await db.execute(insert(TicketLink), link_rows)
    await db.execute(update(Project).where(Project.id == project.id).values(ticket_seq=tickets))
    await db.flush()
    await periods.backfill(db, ids)
    return Seeded(project_key, "fernando@example.com", password, tickets)
