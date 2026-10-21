"""Templates: create, edit and propagate to linked projects; save a project as one."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import (
    Area,
    CustomFieldDefinition,
    Project,
    Status,
    SyncStatus,
    Template,
    TemplateMode,
    TemplateSyncRun,
    Ticket,
    TicketType,
    User,
    UserKind,
    utcnow,
)
from radicle.docket.services import screens
from radicle.docket.services.access import ProjectAccess
from radicle.docket.services.projects import check_description, normalize_name
from radicle.docket.services.template_config import (
    AreaConf,
    FieldConf,
    FieldOptionConf,
    RuleConf,
    ScreenConf,
    ScreenFieldConf,
    SettingsConf,
    StatusConf,
    TemplateConfig,
    TransitionConf,
    WorkflowConf,
    default_config,
    parse,
    parse_workflow,
    slug,
    unreachable,
    workflow_refs,
)
from radicle.docket.services.template_sync import (
    Mappings,
    apply_config,
    apply_workflow,
    parse_mappings,
)
from radicle.docket.services.workflows import load_workflows
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.platform.services import queue

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_TEMPLATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SYNC_JOB = "template_sync"


@dataclass
class TemplateChange:
    template: Template
    runs: list[TemplateSyncRun] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def system_user(db: AsyncSession) -> User:
    user = await db.scalar(select(User).where(User.kind == UserKind.system))
    if user is None:  # pragma: no cover - created by migration 0006
        raise RuntimeError("The system user is missing; run the migrations.")
    return user


def _require_admin(user: User) -> None:
    if not user.is_instance_admin:
        raise Forbidden("Only instance admins can manage templates.")


def _template_not_found(template_id: object) -> NotFound:
    return NotFound(f"Template {template_id} not found.", code="template_not_found")


# --- read ----------------------------------------------------------------------------------


async def list_templates(db: AsyncSession, *, include_archived: bool = False) -> list[Template]:
    query = select(Template)
    if not include_archived:
        query = query.where(Template.archived_at.is_(None))
    return list(await db.scalars(query.order_by(Template.name)))


async def get_template(db: AsyncSession, template_id: uuid.UUID, *, lock: bool = False) -> Template:
    query = select(Template).where(Template.id == template_id)
    if lock:
        query = query.with_for_update()
    template = await db.scalar(query)
    if template is None:
        raise _template_not_found(template_id)
    return template


async def linked_projects(db: AsyncSession, template_ids: list[uuid.UUID]) -> list[Project]:
    if not template_ids:
        return []
    return list(
        await db.scalars(
            select(Project)
            .where(
                Project.template_id.in_(template_ids),
                Project.template_mode == TemplateMode.linked,
            )
            .order_by(Project.key)
        )
    )


async def list_runs(
    db: AsyncSession, template: Template, limit: int = 200
) -> list[TemplateSyncRun]:
    return list(
        await db.scalars(
            select(TemplateSyncRun)
            .where(TemplateSyncRun.template_id == template.id)
            .order_by(TemplateSyncRun.created_at.desc(), TemplateSyncRun.id)
            .limit(limit)
        )
    )


def warnings_for(config: TemplateConfig) -> list[str]:
    warnings = []
    for ticket_type, workflow in config.workflows.items():
        names = unreachable(workflow)
        if names:
            warnings.append(f"In {ticket_type.value}, no transition reaches: {', '.join(names)}.")
    return warnings


# --- write ---------------------------------------------------------------------------------


def _name(value: str) -> str:
    return normalize_name(value, limit=100)


async def create_template(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    description_md: str = "",
    config: dict[str, Any] | None = None,
) -> TemplateChange:
    _require_admin(user)
    parsed = parse(config) if config is not None else default_config()
    template = Template(
        id=uuid.uuid4(),
        name=_name(name),
        description_md=check_description(description_md),
        config=parsed.dump(),
        created_by=user.id,
    )
    db.add(template)
    await db.flush()
    return TemplateChange(template, warnings=warnings_for(parsed))


async def update_template(
    db: AsyncSession,
    user: User,
    template: Template,
    *,
    name: str | None = None,
    description_md: str | None = None,
    config: dict[str, Any] | None = None,
    status_mappings: dict[str, Any] | None = None,
) -> TemplateChange:
    """A config change bumps the version and queues one sync per linked project."""
    _require_admin(user)
    if template.archived_at is not None:
        raise Conflict(
            f"Template '{template.name}' is archived. Restore it to edit.",
            code="template_archived",
        )
    if name is not None:
        template.name = _name(name)
    if description_md is not None:
        template.description_md = check_description(description_md)
    change = TemplateChange(template)
    template.updated_at = utcnow()
    if config is None:
        await db.flush()
        return change

    new = parse(config)
    old = parse(template.config)
    change.warnings = warnings_for(new)
    if new.dump() == old.dump():
        await db.flush()
        return change
    projects = await linked_projects(db, [template.id])
    mappings = parse_mappings(status_mappings, TicketType)
    await _check_removed_statuses(db, old, new, mappings, projects)

    template.config = new.dump()
    template.version += 1
    for project in projects:
        run = TemplateSyncRun(
            id=uuid.uuid4(),
            template_id=template.id,
            template_version=template.version,
            project_id=project.id,
            status_mappings={t.value: m for t, m in mappings.items() if m},
        )
        db.add(run)
        change.runs.append(run)
    await db.flush()
    for run in change.runs:
        await queue.enqueue(db, SYNC_JOB, run_id=str(run.id))
    return change


async def _check_removed_statuses(
    db: AsyncSession,
    old: TemplateConfig,
    new: TemplateConfig,
    mappings: Mappings,
    projects: list[Project],
) -> None:
    errors: list[dict[str, str]] = []
    details: list[str] = []
    for ticket_type, workflow in old.workflows.items():
        new_refs = {s.ref for s in new.workflows[ticket_type].statuses}
        mapping = mappings.get(ticket_type, {})
        for status in workflow.statuses:
            if status.ref in new_refs:
                continue
            target = mapping.get(status.ref)
            if target is not None and target not in new_refs:
                raise ValidationFailed(
                    f"Status mapping for '{status.name}' ({ticket_type.value}) points to "
                    f"'{target}', which is not a status of the new workflow. "
                    f"Use one of: {', '.join(sorted(new_refs))}.",
                    errors=[{"field": "status_mappings", "message": "unknown status"}],
                )
            if target is not None or not projects:
                continue
            counts = await _tickets_in_status(db, projects, ticket_type, status.ref)
            if counts:
                where = ", ".join(f"{n} in {key}" for key, n in counts)
                details.append(f"'{status.name}' ({ticket_type.value}) has tickets: {where}")
                errors.append(
                    {
                        "field": f"status_mappings.{ticket_type.value}.{status.ref}",
                        "message": "required",
                    }
                )
    if errors:
        raise ValidationFailed(
            "Removed statuses still have tickets. Send status_mappings to say where they go, "
            'e.g. {"task": {"in_review": "in_progress"}}. ' + "; ".join(details) + ".",
            code="status_mapping_required",
            errors=errors,
        )


async def _tickets_in_status(
    db: AsyncSession, projects: list[Project], ticket_type: TicketType, ref: str
) -> list[tuple[str, int]]:
    rows = await db.execute(
        select(Project.key, func.count(Ticket.id))
        .join(Status, Status.project_id == Project.id)
        .join(Ticket, Ticket.status_id == Status.id)
        .where(
            Project.id.in_([p.id for p in projects]),
            Status.ticket_type == ticket_type,
            Status.template_ref == ref,
        )
        .group_by(Project.key)
        .order_by(Project.key)
    )
    return [(key, int(n)) for key, n in rows.all()]


def set_archived(user: User, template: Template, archived: bool) -> Template:
    _require_admin(user)
    if template.id == DEFAULT_TEMPLATE_ID and archived:
        raise Conflict("The Radicle default template cannot be archived.", code="default_template")
    template.archived_at = utcnow() if archived else None
    return template


async def retry_run(db: AsyncSession, user: User, run: TemplateSyncRun) -> TemplateSyncRun:
    _require_admin(user)
    if run.status is not SyncStatus.failed:
        raise Conflict("Only failed syncs can be retried.", code="not_failed")
    run.status = SyncStatus.pending
    run.error = None
    run.started_at = None
    run.finished_at = None
    await db.flush()
    await queue.enqueue(db, SYNC_JOB, run_id=str(run.id))
    return run


async def get_run(db: AsyncSession, template: Template, run_id: uuid.UUID) -> TemplateSyncRun:
    run = await db.get(TemplateSyncRun, run_id)
    if run is None or run.template_id != template.id:
        raise NotFound(f"Sync run {run_id} not found.", code="sync_run_not_found")
    return run


@queue.handler(SYNC_JOB)
async def run_sync(db: AsyncSession, run_id: str) -> None:
    """Bring one linked project up to its template. A failure only marks this run."""
    run = await db.get(TemplateSyncRun, uuid.UUID(run_id), with_for_update=True)
    if run is None or run.status is SyncStatus.succeeded:
        return
    template = await db.get(Template, run.template_id)
    project = await db.get(Project, run.project_id, with_for_update=True)
    run.started_at = utcnow()
    if template is None or project is None:  # pragma: no cover - cascades delete runs
        return
    if project.template_id != template.id or project.template_mode is not TemplateMode.linked:
        run.status = SyncStatus.succeeded
        run.finished_at = utcnow()
        return
    run.status = SyncStatus.running
    await db.flush()
    pending = await db.scalars(
        select(TemplateSyncRun).where(
            TemplateSyncRun.template_id == template.id,
            TemplateSyncRun.project_id == project.id,
            TemplateSyncRun.status != SyncStatus.succeeded,
        )
    )
    raw: dict[str, Any] = {}
    for other in sorted(pending, key=lambda r: r.template_version):
        for ticket_type, mapping in (other.status_mappings or {}).items():
            raw.setdefault(ticket_type, {}).update(mapping)
    try:
        async with db.begin_nested():
            await apply_config(
                db,
                project,
                parse(template.config),
                actor=await system_user(db),
                mappings=parse_mappings(raw, TicketType),
            )
            project.template_version = template.version
    except Exception as exc:
        run.status = SyncStatus.failed
        run.error = str(exc) or exc.__class__.__name__
        run.finished_at = utcnow()
        return
    run.status = SyncStatus.succeeded
    run.finished_at = utcnow()


# --- projects and templates ------------------------------------------------------------------


async def instantiate(
    db: AsyncSession,
    project: Project,
    actor: User,
    *,
    template_id: uuid.UUID | None,
    mode: TemplateMode = TemplateMode.linked,
) -> None:
    """Give a new project its configuration. Without a template it uses Radicle default."""
    if template_id is None:
        template = await db.get(Template, DEFAULT_TEMPLATE_ID)
        if template is not None and template.archived_at is not None:  # pragma: no cover
            template = None
    else:
        template = await get_template(db, template_id)
        if template.archived_at is not None:
            raise ValidationFailed(
                f"Template '{template.name}' is archived; pick another one.",
                errors=[{"field": "template_id", "message": "archived"}],
            )
    if template is None:  # pragma: no cover - the default template comes with migrations
        await apply_config(db, project, default_config(), actor=actor)
        return
    await apply_config(db, project, parse(template.config), actor=actor)
    project.template_id = template.id
    project.template_mode = mode
    project.template_version = template.version


def detach(access: ProjectAccess) -> Project:
    project = access.project
    if project.template_mode is not TemplateMode.linked:
        raise Conflict(f"{project.key} is not linked to a template.", code="not_linked")
    project.template_mode = TemplateMode.detached
    project.updated_at = utcnow()
    return project


async def ensure_editable(db: AsyncSession, project: Project) -> None:
    """Workflows, rules, screens and fields of a linked project only change in its template."""
    if project.template_mode is not TemplateMode.linked or project.template_id is None:
        return
    template = await db.get(Template, project.template_id)
    name = template.name if template else "its template"
    raise Conflict(
        f"{project.key} is linked to the template '{name}': change it there, or detach "
        f"{project.key} to edit it here.",
        code="project_linked",
        extra={"template_id": str(project.template_id), "template": name},
    )


async def put_workflow(
    db: AsyncSession,
    access: ProjectAccess,
    ticket_type: TicketType,
    raw: dict[str, Any],
    status_mappings: dict[str, Any] | None,
) -> list[str]:
    """Replace one workflow of an independent project. Tickets in removed statuses with
    no mapping are refused, so nothing moves by surprise."""
    project = access.project
    await ensure_editable(db, project)
    workflow = parse_workflow(raw, ticket_type)
    mapping = parse_mappings(status_mappings, [ticket_type]).get(ticket_type, {})
    refs = {s.ref for s in workflow.statuses}
    current = (await load_workflows(db, project.id))[ticket_type]
    missing: list[str] = []
    for status in current.statuses:
        if status.template_ref in refs:
            continue
        target = mapping.get(status.template_ref or "")
        if target is not None and target not in refs:
            raise ValidationFailed(
                f"Status mapping for '{status.name}' points to '{target}', which is not in the "
                f"new workflow. Use one of: {', '.join(sorted(refs))}.",
                errors=[{"field": "status_mappings", "message": "unknown status"}],
            )
        count = await db.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.status_id == status.id)
        )
        if count and target is None:
            missing.append(f"'{status.name}' ({count} tickets, ref {status.template_ref})")
    if missing:
        raise ValidationFailed(
            "Removed statuses still have tickets; send status_mappings "
            '{"<old ref>": "<new ref>"} for: ' + ", ".join(missing) + ".",
            code="status_mapping_required",
            errors=[{"field": "status_mappings", "message": "required"}],
        )
    await apply_workflow(db, project, ticket_type, workflow, actor=access.user, mapping=mapping)
    project.updated_at = utcnow()
    return [f"No transition reaches: {', '.join(n)}." for n in [unreachable(workflow)] if n]


async def config_from_project(db: AsyncSession, project: Project) -> TemplateConfig:
    workflows = await load_workflows(db, project.id)
    workflow_confs: dict[TicketType, WorkflowConf] = {}
    for ticket_type, workflow in workflows.items():
        refs: dict[uuid.UUID, str] = {}
        for s in workflow.statuses:
            ref = s.template_ref or slug(s.name)
            while ref in refs.values():
                ref += "_2"
            refs[s.id] = ref
        transition_refs = [t.template_ref for t in workflow.transitions]
        generated = workflow_refs(
            [
                (t.name, refs[t.from_status_id] if t.from_status_id else None)
                for t in workflow.transitions
            ]
        )
        workflow_confs[ticket_type] = WorkflowConf(
            statuses=[
                StatusConf(
                    ref=refs[s.id], name=s.name, category=s.category, is_initial=s.is_initial
                )
                for s in workflow.statuses
            ],
            transitions=[
                TransitionConf(
                    ref=ref or generated[i],
                    name=t.name,
                    from_=refs[t.from_status_id] if t.from_status_id else None,
                    to=refs[t.to_status_id],
                    allowed_resolutions=list(t.allowed_resolutions)
                    if t.allowed_resolutions
                    else None,
                    rules=[
                        RuleConf(kind=r.kind.value, rule_type=r.rule_type, config=r.config)
                        for r in workflow.rules_for(t)
                    ],
                )
                for i, (t, ref) in enumerate(
                    zip(workflow.transitions, transition_refs, strict=True)
                )
            ],
        )
    areas = await db.scalars(
        select(Area)
        .where(Area.project_id == project.id, Area.archived_at.is_(None))
        .order_by(Area.position)
    )
    area_list = list(areas)
    area_names = {a.id: a.name for a in area_list}
    fields = await db.scalars(
        select(CustomFieldDefinition)
        .where(
            CustomFieldDefinition.project_id == project.id,
            CustomFieldDefinition.archived_at.is_(None),
        )
        .order_by(CustomFieldDefinition.position)
    )
    transition_refs_by_id: dict[uuid.UUID, str] = {}
    for ticket_type, wf in workflow_confs.items():
        project_wf = workflows[ticket_type]
        for t, conf in zip(project_wf.transitions, wf.transitions, strict=True):
            transition_refs_by_id[t.id] = conf.ref
    screen_confs = [
        ScreenConf(
            type=s.ticket_type,
            operation=s.operation.value,
            transition=transition_refs_by_id.get(s.transition_id) if s.transition_id else None,
            fields=[ScreenFieldConf(**f) for f in s.fields],
        )
        for s in await screens.list_screens(db, project.id)
        if s.transition_id is None or s.transition_id in transition_refs_by_id
    ]
    return TemplateConfig(
        screens=screen_confs,
        areas=[AreaConf(name=a.name, color=a.color) for a in area_list],
        tags=list(project.suggested_tags or []),
        custom_fields=[
            FieldConf(
                ref=f.template_ref or f.key,
                key=f.key,
                name=f.name,
                field_type=f.field_type,
                options=[FieldOptionConf(**o) for o in f.options],
                applies_to_types=list(f.applies_to_types),
                applies_to_areas=(
                    [area_names[a] for a in f.applies_to_area_ids if a in area_names]
                    if f.applies_to_area_ids is not None
                    else None
                ),
            )
            for f in fields
        ],
        workflows=workflow_confs,
        settings=SettingsConf(blocked_policy=project.blocked_policy),
    )


async def save_as_template(
    db: AsyncSession, access: ProjectAccess, *, name: str, description_md: str = ""
) -> TemplateChange:
    """Copies configuration only: no tickets, milestones or members."""
    config = await config_from_project(db, access.project)
    template = Template(
        id=uuid.uuid4(),
        name=_name(name),
        description_md=check_description(description_md),
        config=config.dump(),
        created_by=access.user.id,
    )
    db.add(template)
    await db.flush()
    return TemplateChange(template, warnings=warnings_for(config))
