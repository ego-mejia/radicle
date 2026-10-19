"""Default workflows per ticket type and read access to a project's workflows."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Project,
    Resolution,
    Status,
    StatusCategory,
    TicketType,
    Transition,
)

TODO, IN_PROGRESS, DONE = StatusCategory.todo, StatusCategory.in_progress, StatusCategory.done
R = Resolution


@dataclass(frozen=True)
class TransitionSpec:
    name: str
    from_status: str | None  # None = any status that is not done
    to_status: str
    allowed_resolutions: tuple[Resolution, ...] | None = None  # None = all


@dataclass(frozen=True)
class WorkflowSpec:
    statuses: tuple[tuple[str, StatusCategory], ...]  # first one is initial
    transitions: tuple[TransitionSpec, ...]


DEFAULT_WORKFLOWS: dict[TicketType, WorkflowSpec] = {
    TicketType.task: WorkflowSpec(
        statuses=(
            ("To Do", TODO),
            ("In Progress", IN_PROGRESS),
            ("In Review", IN_PROGRESS),
            ("Done", DONE),
        ),
        transitions=(
            TransitionSpec("Start", "To Do", "In Progress"),
            TransitionSpec("Stop", "In Progress", "To Do"),
            TransitionSpec("Send to review", "In Progress", "In Review"),
            TransitionSpec("Request changes", "In Review", "In Progress"),
            TransitionSpec("Complete", "In Review", "Done"),
            TransitionSpec("Close", None, "Done", (R.wont_do, R.duplicate)),
            TransitionSpec("Reopen", "Done", "To Do"),
        ),
    ),
    TicketType.bug: WorkflowSpec(
        statuses=(
            ("Reported", TODO),
            ("In Progress", IN_PROGRESS),
            ("QA Verified", IN_PROGRESS),
            ("Done", DONE),
        ),
        transitions=(
            TransitionSpec("Start", "Reported", "In Progress"),
            TransitionSpec("Stop", "In Progress", "Reported"),
            TransitionSpec("Send to QA", "In Progress", "QA Verified"),
            TransitionSpec("QA failed", "QA Verified", "In Progress"),
            TransitionSpec("Complete", "QA Verified", "Done"),
            TransitionSpec("Close", None, "Done", (R.wont_do, R.duplicate, R.cannot_reproduce)),
            TransitionSpec("Reopen", "Done", "Reported"),
        ),
    ),
    TicketType.draft: WorkflowSpec(
        statuses=(
            ("New", TODO),
            ("In Review", IN_PROGRESS),
            ("Approved", DONE),
            ("Discarded", DONE),
        ),
        transitions=(
            TransitionSpec("Review", "New", "In Review"),
            TransitionSpec("Approve", "In Review", "Approved", (R.done,)),
            TransitionSpec("Discard", None, "Discarded", (R.wont_do, R.duplicate)),
            TransitionSpec("Reopen", "Approved", "New"),
            TransitionSpec("Reopen", "Discarded", "New"),
        ),
    ),
}


async def seed_default_workflows(db: AsyncSession, project: Project) -> None:
    for ticket_type, spec in DEFAULT_WORKFLOWS.items():
        ids: dict[str, uuid.UUID] = {}
        for position, (name, category) in enumerate(spec.statuses):
            status = Status(
                id=uuid.uuid4(),
                project_id=project.id,
                ticket_type=ticket_type,
                name=name,
                category=category,
                position=position,
                is_initial=position == 0,
            )
            db.add(status)
            ids[name] = status.id
        for position, t in enumerate(spec.transitions):
            db.add(
                Transition(
                    project_id=project.id,
                    ticket_type=ticket_type,
                    name=t.name,
                    from_status_id=ids[t.from_status] if t.from_status else None,
                    to_status_id=ids[t.to_status],
                    allowed_resolutions=(
                        list(t.allowed_resolutions) if t.allowed_resolutions else None
                    ),
                    position=position,
                )
            )
    await db.flush()


@dataclass
class Workflow:
    ticket_type: TicketType
    statuses: list[Status] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)

    def status_by_id(self, status_id: uuid.UUID) -> Status:
        return next(s for s in self.statuses if s.id == status_id)

    def status_named(self, name: str) -> Status | None:
        return next((s for s in self.statuses if s.name.lower() == name.strip().lower()), None)

    @property
    def initial(self) -> Status:
        return next(s for s in self.statuses if s.is_initial)


async def load_workflows(db: AsyncSession, project_id: uuid.UUID) -> dict[TicketType, Workflow]:
    workflows = {t: Workflow(t) for t in TicketType}
    statuses = await db.scalars(
        select(Status).where(Status.project_id == project_id).order_by(Status.position)
    )
    for status in statuses:
        workflows[status.ticket_type].statuses.append(status)
    transitions = await db.scalars(
        select(Transition).where(Transition.project_id == project_id).order_by(Transition.position)
    )
    for transition in transitions:
        workflows[transition.ticket_type].transitions.append(transition)
    return workflows
