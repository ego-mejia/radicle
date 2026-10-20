from fastapi import APIRouter, Response

from radicle.api import serializers as out
from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.schemas.common import Page
from radicle.api.schemas.projects import (
    AreaCreate,
    AreaOut,
    AreaPatch,
    MilestoneCreate,
    MilestoneOut,
    MilestonePatch,
    MilestoneRecapOut,
)
from radicle.api.schemas.tickets import UserRef
from radicle.db.models import MilestoneStatus
from radicle.services import milestone_recap, planning
from radicle.services.access import project_access

router = APIRouter(prefix="/projects/{key}", tags=["areas and milestones"])


@router.get("/areas", response_model=Page[AreaOut])
async def list_areas(
    key: str, principal: CurrentPrincipal, db: Db, include_archived: bool = False
) -> Page[AreaOut]:
    access = await project_access(db, principal.user, key)
    areas = await planning.list_areas(db, access.project, include_archived=include_archived)
    return Page(items=[out.area_out(a) for a in areas])


@router.post("/areas", response_model=AreaOut, status_code=201)
async def create_area(key: str, body: AreaCreate, principal: CurrentPrincipal, db: Db) -> AreaOut:
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    area = await planning.create_area(
        db, access.project, name=body.name, color=body.color, icon=body.icon
    )
    return out.area_out(area)


@router.patch("/areas/{name}", response_model=AreaOut)
async def patch_area(
    key: str, name: str, body: AreaPatch, principal: CurrentPrincipal, db: Db
) -> AreaOut:
    """Rename, recolor, change the icon, reorder, or archive and restore with `archived`."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    area = await planning.get_area(db, access.project, name)
    changes = planning.AreaChanges(
        name=body.name,
        color=body.color,
        clear_color="color" in body.model_fields_set and body.color is None,
        icon=body.icon,
        clear_icon="icon" in body.model_fields_set and body.icon is None,
        position=body.position,
        archived=body.archived,
    )
    return out.area_out(await planning.update_area(db, access.project, area, changes))


@router.delete("/areas/{name}", status_code=204)
async def delete_area(key: str, name: str, principal: CurrentPrincipal, db: Db) -> Response:
    """Archives the area; tickets keep it but new tickets cannot use it."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    planning.archive_area(await planning.get_area(db, access.project, name))
    return Response(status_code=204)


@router.get("/milestones", response_model=Page[MilestoneOut])
async def list_milestones(
    key: str, principal: CurrentPrincipal, db: Db, status: MilestoneStatus | None = None
) -> Page[MilestoneOut]:
    """Milestones with ticket counts per status category, soonest target date first."""
    access = await project_access(db, principal.user, key)
    milestones = await planning.list_milestones(db, access.project, status=status)
    return Page(items=await out.milestones_out(db, milestones))


@router.post("/milestones", response_model=MilestoneOut, status_code=201)
async def create_milestone(
    key: str, body: MilestoneCreate, principal: CurrentPrincipal, db: Db
) -> MilestoneOut:
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    milestone = await planning.create_milestone(
        db,
        access.project,
        name=body.name,
        description_md=body.description_md,
        target_date=body.target_date,
    )
    return (await out.milestones_out(db, [milestone]))[0]


@router.get("/milestones/{name}", response_model=MilestoneOut)
async def get_milestone(key: str, name: str, principal: CurrentPrincipal, db: Db) -> MilestoneOut:
    access = await project_access(db, principal.user, key)
    milestone = await planning.get_milestone(db, access.project, name)
    return (await out.milestones_out(db, [milestone]))[0]


@router.get("/milestones/{name}/recap", response_model=MilestoneRecapOut)
async def get_milestone_recap(
    key: str, name: str, principal: CurrentPrincipal, db: Db
) -> MilestoneRecapOut:
    """Hours, tickets, people and days behind a milestone, for its celebration card."""
    access = await project_access(db, principal.user, key)
    milestone = await planning.get_milestone(db, access.project, name)
    r = await milestone_recap.recap(db, access.project, milestone)
    return MilestoneRecapOut(
        milestone=milestone.name,
        project_key=access.project.key,
        project_name=access.project.name,
        target_date=milestone.target_date,
        complete=r.complete,
        on_time=r.on_time,
        tickets=r.tickets,
        done=r.done,
        tasks=r.by_type.get("task", 0),
        bugs=r.by_type.get("bug", 0),
        ideas=r.by_type.get("draft", 0),
        minutes_logged=r.minutes_logged,
        comments=r.comments,
        humans=r.humans,
        agents=r.agents,
        people=[
            UserRef(handle=u.handle, display_name=u.display_name, kind=u.kind) for u in r.people
        ],
        started_at=r.started_at,
        finished_at=r.finished_at,
        days=r.days,
    )


@router.patch("/milestones/{name}", response_model=MilestoneOut)
async def patch_milestone(
    key: str, name: str, body: MilestonePatch, principal: CurrentPrincipal, db: Db
) -> MilestoneOut:
    """Edit, close (`status: closed`) or reopen (`status: open`)."""
    access = await project_access(
        db, principal.user, key, write=True, permission="project.settings"
    )
    milestone = await planning.get_milestone(db, access.project, name)
    changes = planning.MilestoneChanges(
        name=body.name,
        description_md=body.description_md,
        target_date=body.target_date,
        clear_target_date="target_date" in body.model_fields_set and body.target_date is None,
        status=body.status,
        position=body.position,
    )
    milestone = await planning.update_milestone(db, access.project, milestone, changes)
    return (await out.milestones_out(db, [milestone]))[0]
