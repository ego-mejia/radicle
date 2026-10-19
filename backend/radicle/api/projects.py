from fastapi import APIRouter, Response

from radicle.api import serializers as out
from radicle.api.deps import CurrentPrincipal, Db
from radicle.api.schemas.common import Page
from radicle.api.schemas.projects import (
    MemberOut,
    MemberPut,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectPatch,
    WorkflowOut,
)
from radicle.db.models import ProjectRole
from radicle.services import projects, stats
from radicle.services.access import project_access
from radicle.services.workflows import load_workflows

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=Page[ProjectOut])
async def list_projects(
    principal: CurrentPrincipal, db: Db, include_archived: bool = False
) -> Page[ProjectOut]:
    """Projects where you are a member, with your role. Instance admins see all."""
    rows = await projects.list_projects(db, principal.user, include_archived=include_archived)
    counts = await stats.open_ticket_counts(db, [r.project.id for r in rows])
    return Page(
        items=[out.project_out(r.project, r.role, counts.get(r.project.id, 0)) for r in rows]
    )


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(body: ProjectCreate, principal: CurrentPrincipal, db: Db) -> ProjectDetail:
    """Create a project, seed the Task, Bug and Draft workflows, and make you its admin."""
    project = await projects.create_project(
        db, principal.user, key=body.key, name=body.name, description_md=body.description_md
    )
    return await out.project_detail(db, project, ProjectRole.admin)


@router.get("/{key}", response_model=ProjectDetail)
async def get_project(key: str, principal: CurrentPrincipal, db: Db) -> ProjectDetail:
    """Project with its areas, milestones, workflows and members."""
    access = await project_access(db, principal.user, key)
    return await out.project_detail(db, access.project, access.role)


@router.patch("/{key}", response_model=ProjectDetail)
async def patch_project(
    key: str, body: ProjectPatch, principal: CurrentPrincipal, db: Db
) -> ProjectDetail:
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    await projects.update_project(access, name=body.name, description_md=body.description_md)
    return await out.project_detail(db, access.project, access.role)


@router.post("/{key}/archive", response_model=ProjectDetail)
async def archive_project(key: str, principal: CurrentPrincipal, db: Db) -> ProjectDetail:
    """Archived projects stay visible but become read-only."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin)
    projects.set_archived(access, True)
    return await out.project_detail(db, access.project, access.role)


@router.post("/{key}/unarchive", response_model=ProjectDetail)
async def unarchive_project(key: str, principal: CurrentPrincipal, db: Db) -> ProjectDetail:
    access = await project_access(db, principal.user, key, need=ProjectRole.admin)
    projects.set_archived(access, False)
    return await out.project_detail(db, access.project, access.role)


@router.get("/{key}/workflows", response_model=list[WorkflowOut])
async def get_workflows(key: str, principal: CurrentPrincipal, db: Db) -> list[WorkflowOut]:
    """Statuses and transitions per ticket type."""
    access = await project_access(db, principal.user, key)
    workflows = await load_workflows(db, access.project.id)
    return [out.workflow_out(w) for w in workflows.values()]


@router.get("/{key}/members", response_model=Page[MemberOut])
async def list_members(key: str, principal: CurrentPrincipal, db: Db) -> Page[MemberOut]:
    access = await project_access(db, principal.user, key)
    members = await projects.list_members(db, access.project)
    return Page(items=[out.member_out(m) for m in members])


@router.put("/{key}/members/{handle}", response_model=MemberOut)
async def put_member(
    key: str, handle: str, body: MemberPut, principal: CurrentPrincipal, db: Db
) -> MemberOut:
    """Add a user or agent to the project, or change their role."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    member = await projects.set_member(db, access, handle, body.role)
    return out.member_out(member)


@router.delete("/{key}/members/{handle}", status_code=204)
async def delete_member(key: str, handle: str, principal: CurrentPrincipal, db: Db) -> Response:
    """Remove a member. A project can never be left without an admin."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    await projects.remove_member(db, access, handle)
    return Response(status_code=204)
