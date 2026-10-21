from uuid import UUID

from fastapi import APIRouter, Response

from radicle.docket.api.deps import CurrentPrincipal, Db
from radicle.docket.api.schemas.common import Page
from radicle.docket.api.schemas.security import (
    GrantsPut,
    SecurityLevelCreate,
    SecurityLevelOut,
    SecurityLevelPatch,
)
from radicle.docket.db.models import ProjectRole, SecurityLevel
from radicle.docket.services import security
from radicle.docket.services.access import project_access
from radicle.platform.services import audit

router = APIRouter(tags=["security levels"])


async def _out(db: Db, level: SecurityLevel, count: int | None = None) -> SecurityLevelOut:
    g = await security.grants(db, level)
    if count is None:
        count = (await security.ticket_counts(db, [level])).get(level.id, 0)
    return SecurityLevelOut(
        id=str(level.id),
        name=level.name,
        description=level.description,
        include_participants=level.include_participants,
        groups=g.groups,
        users=g.users,
        ticket_count=count,
    )


@router.get("/projects/{key}/security-levels", response_model=Page[SecurityLevelOut])
async def list_levels(key: str, principal: CurrentPrincipal, db: Db) -> Page[SecurityLevelOut]:
    access = await project_access(db, principal.user, key)
    levels = await security.list_levels(db, access.project)
    counts = await security.ticket_counts(db, levels)
    return Page(items=[await _out(db, lv, counts.get(lv.id, 0)) for lv in levels])


@router.post("/projects/{key}/security-levels", response_model=SecurityLevelOut, status_code=201)
async def create_level(
    key: str, body: SecurityLevelCreate, principal: CurrentPrincipal, db: Db
) -> SecurityLevelOut:
    """A restricted audience for tickets, e.g. "Legal confidencial". Grant it with PUT
    /security-levels/{id}/grants."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    level = await security.create_level(
        db,
        access,
        name=body.name,
        description=body.description,
        include_participants=body.include_participants,
    )
    audit.record(
        db,
        principal.user,
        "security_level.create",
        target_type="security_level",
        target_id=level.id,
        project_id=access.project.id,
        after={"name": level.name, "include_participants": level.include_participants},
    )
    return await _out(db, level, 0)


@router.patch("/security-levels/{level_id}", response_model=SecurityLevelOut)
async def patch_level(
    level_id: UUID, body: SecurityLevelPatch, principal: CurrentPrincipal, db: Db
) -> SecurityLevelOut:
    access, level = await security.load_level(db, principal.user, level_id, admin=True)
    before = {"name": level.name, "include_participants": level.include_participants}
    await security.update_level(
        db,
        level,
        access.project,
        name=body.name,
        description=body.description,
        include_participants=body.include_participants,
    )
    audit.record(
        db,
        principal.user,
        "security_level.update",
        target_type="security_level",
        target_id=level.id,
        project_id=access.project.id,
        before=before,
        after={"name": level.name, "include_participants": level.include_participants},
    )
    return await _out(db, level)


@router.delete("/security-levels/{level_id}", status_code=204)
async def delete_level(level_id: UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """Only levels no ticket uses."""
    access, level = await security.load_level(db, principal.user, level_id, admin=True)
    await security.delete_level(db, level)
    audit.record(
        db,
        principal.user,
        "security_level.delete",
        target_type="security_level",
        target_id=level_id,
        project_id=access.project.id,
        before={"name": level.name},
    )
    return Response(status_code=204)


@router.put("/security-levels/{level_id}/grants", response_model=SecurityLevelOut)
async def put_grants(
    level_id: UUID, body: GrantsPut, principal: CurrentPrincipal, db: Db
) -> SecurityLevelOut:
    """Replace who may see the level's tickets (groups and users)."""
    access, level = await security.load_level(db, principal.user, level_id, admin=True)
    before = await security.grants(db, level)
    after = await security.set_grants(db, level, groups=body.groups, users=body.users)
    audit.record(
        db,
        principal.user,
        "security_level.update",
        target_type="security_level",
        target_id=level.id,
        project_id=access.project.id,
        before={"groups": before.groups, "users": before.users},
        after={"groups": after.groups, "users": after.users},
    )
    return await _out(db, level)
