"""Who sees and does what in Folio (Folio 1.4), through the access service."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioNode,
    FolioPageRestriction,
    FolioRole,
    FolioSpace,
    FolioSpaceGrant,
    GranteeType,
    NodeKind,
    RestrictionMode,
)
from radicle.folio.services import access, nodes, publishing, roles, spaces
from radicle.platform.db.models import Group, User
from radicle.platform.services import groups
from tests.conftest import Team


@pytest.fixture(autouse=True)
def fresh_group_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups, "_cache", {})


async def user(db: AsyncSession, handle: str) -> User:
    found = await db.scalar(select(User).where(User.handle == handle))
    assert found is not None
    return found


@pytest.fixture
async def world(db: AsyncSession, team: Team) -> dict:
    admin = await user(db, team.instance.handle)
    space = await spaces.create_space(db, admin, key="docs", name="Docs")
    page = await nodes.create_node(db, admin, space, kind=NodeKind.page, title="Pública")
    child = await nodes.create_node(
        db, admin, space, kind=NodeKind.page, title="Hija", parent_id=page.id
    )
    draft = await nodes.create_node(db, admin, space, kind=NodeKind.page, title="Borrador")
    folder = await nodes.create_node(db, admin, space, kind=NodeKind.folder, title="Folder")
    for n in (page, child):
        await publishing.create_version(
            db,
            n,
            author=admin,
            content_json={"type": "doc", "content": []},
            metadata={"title": n.title, "labels": []},
            change_note=None,
        )
    return {
        "admin": admin,
        "space": space,
        "page": page,
        "child": child,
        "draft": draft,
        "folder": folder,
    }


async def seen(db: AsyncSession, who: User, space: FolioSpace) -> set[str]:
    ids = await access.visible_ids(db, who, space)
    rows = await db.scalars(select(FolioNode.title).where(FolioNode.id.in_(ids)))
    return set(rows)


async def test_readers_see_published_pages_and_folders(db: AsyncSession, world: dict) -> None:
    luis = await user(db, "luis")
    assert await seen(db, luis, world["space"]) == {"Pública", "Hija", "Folder"}
    assert await seen(db, world["admin"], world["space"]) == {
        "Pública",
        "Hija",
        "Borrador",
        "Folder",
    }
    assert await access.space_permissions(db, luis, world["space"]) == {"view"}


async def test_view_restriction_hides_a_page_and_its_children(
    client: AsyncClient, db: AsyncSession, world: dict, team: Team
) -> None:
    i = team.instance.headers
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo-legal"})
    await client.put("/api/v1/groups/equipo-legal/members/vera", headers=i)
    legal = await db.scalar(select(Group).where(Group.name == "equipo-legal"))
    assert legal is not None
    db.add(
        FolioPageRestriction(
            node_id=world["page"].id,
            mode=RestrictionMode.view,
            grantee_type=GranteeType.group,
            grantee_id=legal.id,
        )
    )
    await db.flush()
    luis, vera = await user(db, "luis"), await user(db, "vera")
    assert await seen(db, luis, world["space"]) == {"Folder"}
    assert not await access.can_view(db, luis, world["child"].id)
    assert await seen(db, vera, world["space"]) == {"Pública", "Hija", "Folder"}
    assert await access.can_view(db, world["admin"], world["child"].id)


async def test_spaces_without_a_grant_are_invisible(db: AsyncSession, world: dict) -> None:
    luis = await user(db, "luis")
    await db.execute(
        FolioSpaceGrant.__table__.delete().where(
            FolioSpaceGrant.grantee_type == GranteeType.everyone
        )
    )
    assert await seen(db, luis, world["space"]) == set()
    assert world["space"].id not in await access.visible_space_ids(db, luis)
    assert world["space"].id in await access.visible_space_ids(db, world["admin"])


async def test_deleted_ancestors_hide_descendants(db: AsyncSession, world: dict) -> None:
    await nodes.delete_node(db, world["admin"], world["page"])
    assert await seen(db, world["admin"], world["space"]) == {"Borrador", "Folder"}


async def test_global_role_caps_space_permissions(db: AsyncSession, world: dict) -> None:
    luis = await user(db, "luis")
    db.add(
        FolioSpaceGrant(
            space_id=world["space"].id,
            grantee_type=GranteeType.user,
            grantee_id=luis.id,
            permissions=["create", "delete_own"],
        )
    )
    await db.flush()
    assert await access.space_permissions(db, luis, world["space"]) == {"view"}
    await roles.set_grant(db, world["admin"], GranteeType.user, "luis", FolioRole.creator)
    perms = await access.space_permissions(db, luis, world["space"])
    assert perms == {"view", "create", "delete_own"}
    assert await access.may_edit(db, luis, world["page"])
    assert not await access.may_delete(db, luis, world["page"])  # someone else's
    assert await seen(db, luis, world["space"]) == {"Pública", "Hija", "Borrador", "Folder"}


async def test_edit_restriction_applies_to_that_page_only(db: AsyncSession, world: dict) -> None:
    luis = await user(db, "luis")
    await roles.set_grant(db, world["admin"], GranteeType.user, "luis", FolioRole.creator)
    db.add(
        FolioSpaceGrant(
            space_id=world["space"].id,
            grantee_type=GranteeType.user,
            grantee_id=luis.id,
            permissions=["create"],
        )
    )
    db.add(
        FolioPageRestriction(
            node_id=world["page"].id,
            mode=RestrictionMode.edit,
            grantee_type=GranteeType.user,
            grantee_id=world["admin"].id,
        )
    )
    await db.flush()
    assert not await access.may_edit(db, luis, world["page"])
    assert await access.may_edit(db, luis, world["child"])
    assert await access.may_edit(db, world["admin"], world["page"])
    assert await access.can_view(db, luis, world["page"].id)  # edit doesn't hide
