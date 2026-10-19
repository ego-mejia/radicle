"""Apply a template configuration to a project, matching everything by `ref`.

The same engine creates a project from a template, propagates template edits to
linked projects and saves the workflow editor of independent projects:

- statuses and transitions are added, renamed, reordered or removed;
- tickets in a removed status move to its mapped status (or the initial one) with a
  `status_remapped` event;
- custom fields are added or updated, and archived when the template drops them;
- areas and tags are only ever added.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import (
    Area,
    CustomFieldDefinition,
    EventType,
    Project,
    Resolution,
    Status,
    StatusCategory,
    Ticket,
    TicketType,
    Transition,
    TransitionRule,
    User,
    utcnow,
)
from radicle.services import custom_fields, history
from radicle.services.template_config import (
    FieldConf,
    TemplateConfig,
    WorkflowConf,
)

# Per ticket type: {old status ref: new status ref}.
Mappings = dict[TicketType, dict[str, str]]


@dataclass
class SyncReport:
    """What changed, for logs and tests."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    remapped_tickets: int = 0


async def apply_config(
    db: AsyncSession,
    project: Project,
    config: TemplateConfig,
    *,
    actor: User,
    mappings: Mappings | None = None,
) -> SyncReport:
    report = SyncReport()
    await add_areas(db, project, config)
    project.suggested_tags = sorted(set(project.suggested_tags or []) | set(config.tags))
    for ticket_type, workflow in config.workflows.items():
        await apply_workflow(
            db,
            project,
            ticket_type,
            workflow,
            actor=actor,
            mapping=(mappings or {}).get(ticket_type, {}),
            report=report,
        )
    await apply_fields(db, project, config.custom_fields, report)
    project.blocked_policy = config.settings.blocked_policy
    await db.flush()
    return report


async def add_areas(db: AsyncSession, project: Project, config: TemplateConfig) -> None:
    existing = {
        name.lower()
        for name in await db.scalars(select(Area.name).where(Area.project_id == project.id))
    }
    position = await db.scalar(select(func.max(Area.position)).where(Area.project_id == project.id))
    next_position = 0 if position is None else position + 1
    for area in config.areas:
        if area.name.lower() in existing:
            continue
        db.add(
            Area(
                project_id=project.id,
                name=area.name,
                color=area.color.upper() if area.color else None,
                position=next_position,
            )
        )
        existing.add(area.name.lower())
        next_position += 1


async def apply_workflow(
    db: AsyncSession,
    project: Project,
    ticket_type: TicketType,
    workflow: WorkflowConf,
    *,
    actor: User,
    mapping: dict[str, str],
    report: SyncReport | None = None,
) -> None:
    report = report if report is not None else SyncReport()
    statuses = list(
        await db.scalars(
            select(Status).where(Status.project_id == project.id, Status.ticket_type == ticket_type)
        )
    )
    by_ref = {s.template_ref: s for s in statuses if s.template_ref}
    wanted = {s.ref for s in workflow.statuses}
    removed = [s for s in statuses if s.template_ref not in wanted]

    original_names = {s.id: s.name for s in statuses}
    # Free names and the initial flag first: unique indexes would trip on swaps.
    for s in statuses:
        s.name = f"{s.name} ~{s.id}"
        s.is_initial = False
    await db.flush()

    new_by_ref: dict[str, Status] = {}
    for position, conf in enumerate(workflow.statuses):
        status = by_ref.get(conf.ref)
        if status is None:
            status = Status(
                id=uuid.uuid4(),
                project_id=project.id,
                ticket_type=ticket_type,
                template_ref=conf.ref,
                name=conf.name,
                category=conf.category,
                position=position,
            )
            db.add(status)
            report.added.append(f"{ticket_type.value}:{conf.ref}")
        status.name = conf.name
        status.category = conf.category
        status.position = position
        new_by_ref[conf.ref] = status
    await db.flush()
    initial = next(new_by_ref[c.ref] for c in workflow.statuses if c.is_initial)
    initial.is_initial = True
    await db.flush()

    for old in removed:
        target = new_by_ref.get(mapping.get(old.template_ref or "", ""), initial)
        report.remapped_tickets += await _move_tickets(
            db, old, original_names[old.id], target, actor
        )
        report.removed.append(f"{ticket_type.value}:{old.template_ref}")
    if removed:
        await db.execute(delete(Status).where(Status.id.in_([s.id for s in removed])))

    await _apply_transitions(db, project, ticket_type, workflow, new_by_ref)
    await db.flush()


async def _move_tickets(
    db: AsyncSession, old: Status, old_name: str, target: Status, actor: User
) -> int:
    """Every ticket in `old` (deleted ones too) goes to `target`, with history."""
    from radicle.services.tickets import bump

    tickets = list(await db.scalars(select(Ticket).where(Ticket.status_id == old.id)))
    for ticket in tickets:
        old_value = {"status": old_name, "resolution": _value(ticket.resolution)}
        ticket.status_id = target.id
        ticket.status = target
        if target.category is StatusCategory.done:
            ticket.resolution = ticket.resolution or Resolution.done
            ticket.resolved_at = ticket.resolved_at or utcnow()
        else:
            ticket.resolution = None
            ticket.resolved_at = None
        history.record(
            db,
            ticket,
            actor,
            EventType.status_remapped,
            field="status",
            old=old_value,
            new={"status": target.name, "resolution": _value(ticket.resolution)},
        )
        bump(ticket)
    await db.flush()
    return len(tickets)


async def _apply_transitions(
    db: AsyncSession,
    project: Project,
    ticket_type: TicketType,
    workflow: WorkflowConf,
    statuses: dict[str, Status],
) -> None:
    existing = list(
        await db.scalars(
            select(Transition).where(
                Transition.project_id == project.id, Transition.ticket_type == ticket_type
            )
        )
    )
    by_ref: dict[str, Transition] = {t.template_ref: t for t in existing if t.template_ref}
    wanted = {t.ref for t in workflow.transitions}
    stale = [t.id for t in existing if t.template_ref not in wanted]
    if stale:
        await db.execute(delete(Transition).where(Transition.id.in_(stale)))
    for position, conf in enumerate(workflow.transitions):
        transition = by_ref.get(conf.ref)
        if transition is None:
            transition = Transition(
                id=uuid.uuid4(),
                project_id=project.id,
                ticket_type=ticket_type,
                template_ref=conf.ref,
                position=position,
                to_status_id=statuses[conf.to].id,
                name=conf.name,
            )
            db.add(transition)
            by_ref[conf.ref] = transition
        transition.name = conf.name
        transition.from_status_id = statuses[conf.from_].id if conf.from_ else None
        transition.to_status_id = statuses[conf.to].id
        transition.allowed_resolutions = (
            list(conf.allowed_resolutions) if conf.allowed_resolutions else None
        )
        transition.position = position
    await db.flush()
    await _apply_rules(db, workflow, by_ref)


async def _apply_rules(
    db: AsyncSession, workflow: WorkflowConf, transitions: dict[str, Transition]
) -> None:
    """Rules are small and ordered: replace them when they differ."""
    for conf in workflow.transitions:
        transition = transitions.get(conf.ref)
        if transition is None:  # pragma: no cover - every configured ref exists by now
            continue
        wanted = [(r.kind, r.rule_type, dict(r.config)) for r in conf.rules]
        current = list(
            await db.scalars(
                select(TransitionRule)
                .where(TransitionRule.transition_id == transition.id)
                .order_by(TransitionRule.position)
            )
        )
        if [(r.kind.value, r.rule_type, r.config) for r in current] == wanted:
            continue
        await db.execute(
            delete(TransitionRule).where(TransitionRule.transition_id == transition.id)
        )
        for position, (kind, rule_type, config) in enumerate(wanted):
            db.add(
                TransitionRule(
                    transition_id=transition.id,
                    kind=kind,
                    rule_type=rule_type,
                    config=config,
                    position=position,
                )
            )
    await db.flush()


async def apply_fields(
    db: AsyncSession, project: Project, fields: list[FieldConf], report: SyncReport
) -> None:
    existing = list(
        await db.scalars(
            select(CustomFieldDefinition).where(CustomFieldDefinition.project_id == project.id)
        )
    )
    by_ref = {f.template_ref: f for f in existing if f.template_ref}
    by_key = {f.key: f for f in existing}
    wanted = {f.ref for f in fields}
    for f in existing:
        if f.template_ref and f.template_ref not in wanted and f.archived_at is None:
            f.archived_at = utcnow()
            report.removed.append(f"field:{f.key}")
    for position, conf in enumerate(fields):
        options = custom_fields.normalize_options(
            conf.field_type, [o.model_dump() for o in conf.options] or None
        )
        areas = await _area_ids(db, project, conf.applies_to_areas)
        definition = by_ref.get(conf.ref) or by_key.get(conf.key)
        if definition is None:
            definition = CustomFieldDefinition(
                project_id=project.id,
                key=custom_fields.normalize_key(conf.key),
                field_type=conf.field_type,
            )
            db.add(definition)
            report.added.append(f"field:{conf.key}")
        elif definition.field_type is not conf.field_type:
            raise ValueError(
                f"Field '{conf.key}' is a {definition.field_type.value} in {project.key}, "
                f"but the template says {conf.field_type.value}."
            )
        definition.template_ref = conf.ref
        definition.name = conf.name
        definition.options = options
        definition.applies_to_types = (
            [t for t in TicketType if t in set(conf.applies_to_types)]
            if conf.applies_to_types
            else list(TicketType)
        )
        definition.applies_to_area_ids = areas
        definition.position = position
        definition.archived_at = None
    await db.flush()


async def _area_ids(
    db: AsyncSession, project: Project, names: Iterable[str] | None
) -> list[uuid.UUID] | None:
    if names is None:
        return None
    wanted = [n.lower() for n in names]
    rows = await db.execute(
        select(Area.id, func.lower(Area.name)).where(Area.project_id == project.id)
    )
    found = dict((name, aid) for aid, name in rows.all())
    return [found[n] for n in wanted if n in found]


def _value(resolution: Resolution | None) -> str | None:
    return resolution.value if resolution is not None else None


def parse_mappings(raw: dict[str, Any] | None, types: Iterable[TicketType]) -> Mappings:
    """Accept `{"old": "new"}` (applies to every type) or `{"task": {"old": "new"}}`."""
    result: Mappings = {t: {} for t in types}
    for key, value in (raw or {}).items():
        if isinstance(value, dict):
            try:
                ticket_type = TicketType(key)
            except ValueError:
                continue
            result.setdefault(ticket_type, {}).update({str(k): str(v) for k, v in value.items()})
        else:
            for mapping in result.values():
                mapping[str(key)] = str(value)
    return result
