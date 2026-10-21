"""Folio spaces (Folio 1.1), through the service: keys, personal spaces, permissions."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import SpaceKind
from radicle.folio.services import spaces
from radicle.platform.db.models import User
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed
from tests.conftest import Team


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def admin(db: AsyncSession, team: Team) -> User:
    return await _user(db, team.instance.handle)


async def test_spaces_keys_personal_and_permissions(db: AsyncSession, admin: User) -> None:
    luis = await _user(db, "luis")
    with pytest.raises(ValidationFailed, match="ai-tools"):
        await spaces.create_space(db, admin, key="AI Tools", name="X")
    await spaces.create_space(db, admin, key="legal", name="Legal")
    with pytest.raises(Conflict, match="taken"):
        await spaces.create_space(db, admin, key="LEGAL", name="Otro")
    with pytest.raises(Forbidden, match="reader"):
        await spaces.create_space(db, luis, key="mine", name="Mío")

    mine = await spaces.personal_space(db, luis)
    assert mine.kind == SpaceKind.personal and mine.key == "me-luis"
    assert (await spaces.personal_space(db, luis)).id == mine.id
    assert {s.key for s in await spaces.list_spaces(db, luis)} == {"legal", "me-luis"}
    assert "me-luis" not in {s.key for s in await spaces.list_spaces(db, admin)}
    with pytest.raises(NotFound):
        await spaces.get_space(db, admin, "me-luis")
    with pytest.raises(ValidationFailed, match="cannot be deleted"):
        await spaces.delete_space(db, luis, mine)

    legal = await spaces.get_space(db, luis, "legal")
    with pytest.raises(Forbidden, match="admins of Legal"):
        await spaces.update_space(db, luis, legal, spaces.SpaceChanges(name="Nope"))
    await spaces.delete_space(db, admin, legal)
    with pytest.raises(NotFound):
        await spaces.get_space(db, luis, "legal")


async def test_edit_a_space(db: AsyncSession, admin: User) -> None:
    space = await spaces.create_space(db, admin, key="eng", name="Eng", icon="code")
    changes = spaces.SpaceChanges(name=" Ingeniería ", description="Cómo construimos.")
    await spaces.update_space(db, admin, space, changes)
    assert (space.name, space.description, space.icon) == (
        "Ingeniería",
        "Cómo construimos.",
        "code",
    )
    await spaces.update_space(db, admin, space, spaces.SpaceChanges(clear_icon=True))
    assert space.icon is None
    with pytest.raises(ValidationFailed, match="1 to 120"):
        await spaces.update_space(db, admin, space, spaces.SpaceChanges(name=""))
    with pytest.raises(ValidationFailed, match="up to 1000"):
        await spaces.update_space(db, admin, space, spaces.SpaceChanges(description="x" * 1001))
