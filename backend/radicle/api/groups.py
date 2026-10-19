from fastapi import APIRouter, Response

from radicle.api.deps import CurrentPrincipal, Db, InstanceAdmin
from radicle.api.schemas.common import Page
from radicle.api.schemas.groups import (
    GroupCreate,
    GroupDetail,
    GroupOut,
    GroupPatch,
    GroupRoleOut,
    GroupRolePut,
    PermissionRow,
    PermissionsOut,
    PermissionsPut,
)
from radicle.api.ticket_views import user_ref
from radicle.db.models import Group, Project, ProjectRole
from radicle.services import audit, groups, permission_matrix
from radicle.services.access import project_access

router = APIRouter(tags=["groups and permissions"])


async def _group_out(db: Db, group: Group, count: int | None = None) -> GroupOut:
    if count is None:
        count = len(await groups.members(db, group))
    return GroupOut(
        name=group.name,
        description=group.description,
        member_count=count,
        created_at=group.created_at,
    )


async def _detail(db: Db, group: Group) -> GroupDetail:
    people = await groups.members(db, group)
    base = await _group_out(db, group, len(people))
    return GroupDetail(**base.model_dump(), members=[user_ref(u) for u in people])


@router.get("/groups", response_model=Page[GroupOut])
async def list_groups(_: InstanceAdmin, db: Db) -> Page[GroupOut]:
    counts = await groups.member_counts(db)
    return Page(
        items=[await _group_out(db, g, counts.get(g.id, 0)) for g in await groups.list_groups(db)]
    )


@router.post("/groups", response_model=GroupDetail, status_code=201)
async def create_group(body: GroupCreate, admin: InstanceAdmin, db: Db) -> GroupDetail:
    """Instance admins create groups; they hold humans and agents."""
    group = await groups.create_group(db, body.name, body.description)
    audit.record(
        db,
        admin,
        "group.create",
        target_type="group",
        target_id=group.name,
        after={"name": group.name, "description": group.description},
    )
    return await _detail(db, group)


@router.get("/groups/{name}", response_model=GroupDetail)
async def get_group(name: str, _: InstanceAdmin, db: Db) -> GroupDetail:
    return await _detail(db, await groups.get_group(db, name))


@router.patch("/groups/{name}", response_model=GroupDetail)
async def patch_group(name: str, body: GroupPatch, admin: InstanceAdmin, db: Db) -> GroupDetail:
    group = await groups.get_group(db, name)
    before = {"name": group.name, "description": group.description}
    await groups.update_group(db, group, name=body.name, description=body.description)
    audit.record(
        db,
        admin,
        "group.update",
        target_type="group",
        target_id=group.name,
        before=before,
        after={"name": group.name, "description": group.description},
    )
    return await _detail(db, group)


@router.delete("/groups/{name}", status_code=204)
async def delete_group(name: str, admin: InstanceAdmin, db: Db) -> Response:
    await groups.delete_group(db, await groups.get_group(db, name))
    audit.record(db, admin, "group.delete", target_type="group", target_id=name)
    return Response(status_code=204)


@router.put("/groups/{name}/members/{handle}", response_model=GroupDetail)
async def add_group_member(name: str, handle: str, admin: InstanceAdmin, db: Db) -> GroupDetail:
    group = await groups.get_group(db, name)
    user = await groups.add_member(db, group, handle)
    audit.record(
        db, admin, "group.member_add", target_type="group", target_id=group.name, member=user.handle
    )
    return await _detail(db, group)


@router.delete("/groups/{name}/members/{handle}", response_model=GroupDetail)
async def remove_group_member(name: str, handle: str, admin: InstanceAdmin, db: Db) -> GroupDetail:
    group = await groups.get_group(db, name)
    user = await groups.remove_member(db, group, handle)
    audit.record(
        db,
        admin,
        "group.member_remove",
        target_type="group",
        target_id=group.name,
        member=user.handle,
    )
    return await _detail(db, group)


@router.get("/projects/{key}/group-roles", response_model=Page[GroupRoleOut])
async def list_group_roles(key: str, principal: CurrentPrincipal, db: Db) -> Page[GroupRoleOut]:
    access = await project_access(db, principal.user, key)
    counts = await groups.member_counts(db)
    return Page(
        items=[
            GroupRoleOut(group=g.name, role=r, member_count=counts.get(g.id, 0))
            for g, r in await groups.project_groups(db, access.project)
        ]
    )


@router.put("/projects/{key}/group-roles/{group}", response_model=GroupRoleOut)
async def put_group_role(
    key: str, group: str, body: GroupRolePut, principal: CurrentPrincipal, db: Db
) -> GroupRoleOut:
    """Every member of the group gets this role in the project (their highest role wins)."""
    access = await project_access(db, principal.user, key, write=True, permission="members.manage")
    g = await groups.get_group(db, group)
    previous = await groups.set_group_role(db, access, g, body.role)
    audit.record(
        db,
        principal.user,
        "group_role.add",
        target_type="group",
        target_id=g.name,
        project_id=access.project.id,
        before={"role": previous.value} if previous else None,
        after={"role": body.role.value},
    )
    return GroupRoleOut(group=g.name, role=body.role, member_count=len(await groups.members(db, g)))


@router.delete("/projects/{key}/group-roles/{group}", status_code=204)
async def delete_group_role(key: str, group: str, principal: CurrentPrincipal, db: Db) -> Response:
    access = await project_access(db, principal.user, key, write=True, permission="members.manage")
    role = await groups.remove_group_role(db, access, await groups.get_group(db, group))
    audit.record(
        db,
        principal.user,
        "group_role.remove",
        target_type="group",
        target_id=group,
        project_id=access.project.id,
        before={"role": role.value},
    )
    return Response(status_code=204)


async def _matrix(db: Db, project: Project) -> PermissionsOut:
    rows = await permission_matrix.read(db, project)
    return PermissionsOut(project=project.key, rows=[PermissionRow(**r.__dict__) for r in rows])


@router.get("/projects/{key}/permissions", response_model=PermissionsOut)
async def get_permissions(key: str, principal: CurrentPrincipal, db: Db) -> PermissionsOut:
    """What member and viewer may do in this project. Admins may do everything."""
    access = await project_access(db, principal.user, key)
    return await _matrix(db, access.project)


@router.put("/projects/{key}/permissions", response_model=PermissionsOut)
async def put_permissions(
    key: str, body: PermissionsPut, principal: CurrentPrincipal, db: Db
) -> PermissionsOut:
    """Turn permissions on or off for member and viewer. Only what you send changes."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    changed = await permission_matrix.change(
        db, access.project, {ProjectRole.member: body.member, ProjectRole.viewer: body.viewer}
    )
    for role, perm, old, new in changed:
        audit.record(
            db,
            principal.user,
            "permission.change",
            target_type="permission",
            target_id=f"{role.value}:{perm}",
            project_id=access.project.id,
            before={"allowed": old},
            after={"allowed": new},
        )
    return await _matrix(db, access.project)


@router.delete("/projects/{key}/permissions", response_model=PermissionsOut)
async def reset_permissions(key: str, principal: CurrentPrincipal, db: Db) -> PermissionsOut:
    """Back to the defaults of the catalog."""
    access = await project_access(db, principal.user, key, need=ProjectRole.admin, write=True)
    await permission_matrix.reset(db, access.project)
    audit.record(
        db,
        principal.user,
        "permission.change",
        target_type="permission",
        target_id="*",
        project_id=access.project.id,
        reset=True,
    )
    return await _matrix(db, access.project)
