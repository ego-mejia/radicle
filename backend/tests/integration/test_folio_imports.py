"""Imports (Folio 5.3): uploading an export into a space, and who may."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.imports import ImportSource, ImportStatus
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import imports
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from radicle.platform.storage import get_storage
from tests.conftest import Team
from tests.folio_import_fixtures import zipped
from tests.integration.folio_helpers import API


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def space(client: AsyncClient, db: AsyncSession, team: Team) -> FolioSpace:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    found = await db.scalar(select(FolioSpace).where(FolioSpace.key == "eng"))
    assert found is not None
    return found


async def test_an_upload_is_kept_and_creates_nothing(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, "fernando")
    data = zipped("confluence")
    item = await imports.create(
        db, fernando, space, source=ImportSource.confluence, filename="ENG.zip", data=data
    )
    assert item.status == ImportStatus.uploaded and item.created_by == fernando.id
    assert await get_storage().get(item.upload_key) == data
    assert (await imports.get(db, fernando, item.id)).id == item.id
    assert [i.id for i in await imports.list_imports(db, fernando)] == [item.id]
    found = await imports.read_bundle(item)
    assert [p.title for p in found.pages][:2] == ["Home", "Guías"]
    assert await db.scalar(select(FolioNode).where(FolioNode.space_id == space.id)) is None


async def test_only_space_admins_import(db: AsyncSession, team: Team, space: FolioSpace) -> None:
    fernando, luis = await _user(db, "fernando"), await _user(db, "luis")
    with pytest.raises(Forbidden, match="Only the admins of Ingeniería"):
        await imports.create(
            db, luis, space, source=ImportSource.markdown, filename="a.md", data=b"# A"
        )
    with pytest.raises(ValidationFailed, match="empty"):
        await imports.create(
            db, fernando, space, source=ImportSource.markdown, filename="a.md", data=b""
        )
    item = await imports.create(
        db, fernando, space, source=ImportSource.markdown, filename="a.md", data=b"# A"
    )
    with pytest.raises(Forbidden):
        await imports.get(db, luis, item.id)
    assert await imports.list_imports(db, luis) == []
    with pytest.raises(NotFound, match="doesn't exist"):
        await imports.get(db, fernando, fernando.id)
