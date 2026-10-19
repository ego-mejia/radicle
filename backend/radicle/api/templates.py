from uuid import UUID

from fastapi import APIRouter

from radicle.api.deps import CurrentPrincipal, Db, InstanceAdmin
from radicle.api.schemas.common import Page
from radicle.api.schemas.templates import (
    LinkedProjectOut,
    SyncRunOut,
    TemplateCreate,
    TemplateDetail,
    TemplateOut,
    TemplatePatch,
    config_dict,
)
from radicle.db.models import Project, Template, TemplateSyncRun
from radicle.services import templates
from radicle.services.template_config import parse

router = APIRouter(prefix="/templates", tags=["templates"])


async def template_out(db: Db, rows: list[Template]) -> list[TemplateOut]:
    projects = await templates.linked_projects(db, [t.id for t in rows])
    result = []
    for t in rows:
        linked = [p for p in projects if p.template_id == t.id]
        result.append(
            TemplateOut(
                id=str(t.id),
                name=t.name,
                description_md=t.description_md,
                version=t.version,
                archived=t.archived_at is not None,
                is_default=t.id == templates.DEFAULT_TEMPLATE_ID,
                linked_projects=[
                    LinkedProjectOut(
                        key=p.key,
                        name=p.name,
                        template_version=p.template_version,
                        in_sync=p.template_version == t.version,
                    )
                    for p in linked
                ],
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )
    return result


async def template_detail(db: Db, template: Template, warnings: list[str]) -> TemplateDetail:
    base = (await template_out(db, [template]))[0]
    return TemplateDetail(**base.model_dump(), config=parse(template.config), warnings=warnings)


def run_out(run: TemplateSyncRun, keys: dict[UUID, str]) -> SyncRunOut:
    return SyncRunOut(
        id=str(run.id),
        project=keys.get(run.project_id, "?"),
        template_version=run.template_version,
        status=run.status,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


async def runs_out(db: Db, runs: list[TemplateSyncRun]) -> list[SyncRunOut]:
    ids = {r.project_id for r in runs}
    keys = {}
    for project_id in ids:
        project = await db.get(Project, project_id)
        if project is not None:
            keys[project_id] = project.key
    return [run_out(r, keys) for r in runs]


@router.get("", response_model=Page[TemplateOut])
async def list_templates(
    principal: CurrentPrincipal, db: Db, include_archived: bool = False
) -> Page[TemplateOut]:
    """Templates to create projects from, with the projects linked to each."""
    rows = await templates.list_templates(db, include_archived=include_archived)
    return Page(items=await template_out(db, rows))


@router.post("", response_model=TemplateDetail, status_code=201)
async def create_template(body: TemplateCreate, user: InstanceAdmin, db: Db) -> TemplateDetail:
    change = await templates.create_template(
        db,
        user,
        name=body.name,
        description_md=body.description_md,
        config=config_dict(body.config),
    )
    return await template_detail(db, change.template, change.warnings)


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(template_id: UUID, principal: CurrentPrincipal, db: Db) -> TemplateDetail:
    template = await templates.get_template(db, template_id)
    return await template_detail(db, template, templates.warnings_for(parse(template.config)))


@router.patch("/{template_id}", response_model=TemplateDetail)
async def patch_template(
    template_id: UUID, body: TemplatePatch, user: InstanceAdmin, db: Db
) -> TemplateDetail:
    """Removing a status that still has tickets in linked projects needs `status_mappings`."""
    template = await templates.get_template(db, template_id, lock=True)
    change = await templates.update_template(
        db,
        user,
        template,
        name=body.name,
        description_md=body.description_md,
        config=config_dict(body.config),
        status_mappings=body.status_mappings,
    )
    return await template_detail(db, template, change.warnings)


@router.post("/{template_id}/archive", response_model=TemplateDetail)
async def archive_template(template_id: UUID, user: InstanceAdmin, db: Db) -> TemplateDetail:
    """Archived templates cannot create projects; linked projects keep their configuration."""
    template = templates.set_archived(user, await templates.get_template(db, template_id), True)
    return await template_detail(db, template, [])


@router.post("/{template_id}/unarchive", response_model=TemplateDetail)
async def unarchive_template(template_id: UUID, user: InstanceAdmin, db: Db) -> TemplateDetail:
    template = templates.set_archived(user, await templates.get_template(db, template_id), False)
    return await template_detail(db, template, [])


@router.get("/{template_id}/sync-runs", response_model=Page[SyncRunOut])
async def list_sync_runs(template_id: UUID, user: InstanceAdmin, db: Db) -> Page[SyncRunOut]:
    """Propagation progress: one run per linked project and version, newest first."""
    template = await templates.get_template(db, template_id)
    return Page(items=await runs_out(db, await templates.list_runs(db, template)))


@router.post("/{template_id}/sync-runs/{run_id}/retry", response_model=SyncRunOut)
async def retry_sync_run(
    template_id: UUID, run_id: UUID, user: InstanceAdmin, db: Db
) -> SyncRunOut:
    template = await templates.get_template(db, template_id)
    run = await templates.retry_run(db, user, await templates.get_run(db, template, run_id))
    return (await runs_out(db, [run]))[0]
