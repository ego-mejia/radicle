"""Realistic demo and benchmark data. Used by scripts/seed.py and the performance test."""

import random
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core import security
from radicle.db.models import (
    Area,
    LinkType,
    Milestone,
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
from radicle.services import rank
from radicle.services.templates import instantiate

AREAS = ["Legal", "Marketing", "Backend", "Frontend", "Mobile", "Data", "Infra", "Design"]
WORDS = (
    "pagos login checkout api webhook factura reporte usuario búsqueda tablero perfil correo "
    "notificación permisos exportar importar móvil carrito envío inventario contrato términos "
    "onboarding métricas caché sesión token archivo imagen calendario"
).split()
TAGS = ["backlog", "pagos", "ux", "tech-debt", "security", "perf", "mobile", "copy", "infra"]
HUMANS = ["fernando", "ana", "luis", "vera", "marta", "jorge"]
AGENTS = ["agent-backend", "agent-frontend", "agent-qa"]


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

    project = Project(key=project_key, name=f"Proyecto {project_key}", created_by=users[0].id)
    db.add(project)
    await db.flush()
    await instantiate(db, project, users[0], template_id=None)
    from radicle.services.boards import create_default_board

    await create_default_board(db, project, users[0])
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
        created = now - timedelta(minutes=rng.randint(0, 60 * 24 * 180))
        current_rank = rank.after(current_rank)
        ticket_id = uuid.uuid4()
        ids.append(ticket_id)
        reporter = rng.choice(assignable)
        rows.append(
            {
                "id": ticket_id,
                "project_id": project.id,
                "number": number,
                "type": ticket_type,
                "title": " ".join(rng.sample(WORDS, 3)).capitalize(),
                "description_md": " ".join(rng.choices(WORDS, k=25))
                + "\n\n- [x] Primer paso\n- [ ] Segundo paso",
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
                "due_date": (created + timedelta(days=rng.randint(1, 90))).date()
                if rng.random() < 0.4
                else None,
                "estimate_hours": rng.choice([None, 1, 2, 3, 5, 8, 13]),
                "tags": rng.sample(TAGS, rng.randint(0, 3)),
                "rank": current_rank,
                "created_at": created,
                "updated_at": created + timedelta(hours=rng.randint(0, 200)),
                "resolved_at": created + timedelta(days=2) if done else None,
            }
        )
        events.append(
            {
                "ticket_id": ticket_id,
                "actor_id": reporter.id,
                "event_type": "created",
                "new_value": {"type": ticket_type.value},
                "created_at": created,
            }
        )
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
    return Seeded(project_key, "fernando@example.com", password, tickets)
