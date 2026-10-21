"""Folio's global roles (Folio 0.5): the effective role and Folio's authz provider."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioGlobalGrant, FolioRole, GranteeType
from radicle.folio.services import roles
from radicle.platform import authz
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import groups
from tests.conftest import Team


@pytest.fixture(autouse=True)
def fresh_group_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups, "_cache", {})


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


async def test_everyone_reads_and_instance_admins_administer(db: AsyncSession, team: Team) -> None:
    luis, admin = await _user(db, "luis"), await _user(db, team.instance.handle)
    assert await roles.effective_role(db, luis) == FolioRole.reader
    assert await roles.effective_role(db, admin) == FolioRole.admin
    assert [(g.grantee_type, g.role) for g in await roles.list_grants(db)] == [
        (GranteeType.everyone, FolioRole.reader)
    ]


async def test_highest_of_direct_group_and_everyone(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i = team.instance.headers
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo-docs"})
    await client.put("/api/v1/groups/equipo-docs/members/luis", headers=i)
    admin, luis, vera = [await _user(db, h) for h in (team.instance.handle, "luis", "vera")]

    await roles.set_grant(db, admin, GranteeType.group, "equipo-docs", FolioRole.creator)
    assert await roles.effective_role(db, luis) == FolioRole.creator
    assert await roles.effective_role(db, vera) == FolioRole.reader

    _, previous = await roles.set_grant(db, admin, GranteeType.user, "@vera", FolioRole.admin)
    assert previous is None
    _, previous = await roles.set_grant(db, admin, GranteeType.user, "vera", FolioRole.creator)
    assert previous == FolioRole.admin
    assert await roles.effective_role(db, vera) == FolioRole.creator
    listed = [(g.grantee_type.value, g.grantee) for g in await roles.list_grants(db)]
    assert listed == [("everyone", None), ("group", "equipo-docs"), ("user", "vera")]


async def test_no_grant_means_no_access(db: AsyncSession, team: Team) -> None:
    await db.execute(delete(FolioGlobalGrant))
    luis = await _user(db, "luis")
    assert await roles.effective_role(db, luis) is None
    decision = await authz.authorize(db, luis, "folio", "folio.read")
    assert not decision.allowed and decision.status == 404
    assert "no access to Folio" in decision.reason


async def test_provider_checks_the_role_each_permission_needs(db: AsyncSession, team: Team) -> None:
    luis, admin = await _user(db, "luis"), await _user(db, team.instance.handle)
    assert (await authz.authorize(db, luis, "folio", "folio.read")).allowed
    creating = await authz.authorize(db, luis, "folio", "folio.create")
    assert not creating.allowed and creating.status == 403 and "reader" in creating.reason
    assert not (await authz.authorize(db, luis, "folio", "folio.nope")).allowed
    assert (await authz.authorize(db, admin, "folio", "folio.admin")).allowed


async def test_actionable_errors(db: AsyncSession, team: Team) -> None:
    admin = await _user(db, team.instance.handle)
    with pytest.raises(ValidationFailed, match="handle or a group"):
        await roles.set_grant(db, admin, GranteeType.group, None, FolioRole.reader)
    with pytest.raises(ValidationFailed, match="leave it empty"):
        await roles.set_grant(db, admin, GranteeType.everyone, "luis", FolioRole.reader)
    with pytest.raises(NotFound):
        await roles.set_grant(db, admin, GranteeType.group, "nope", FolioRole.reader)
    with pytest.raises(NotFound, match="lists them"):
        await roles.remove_grant(db, uuid.uuid4())
