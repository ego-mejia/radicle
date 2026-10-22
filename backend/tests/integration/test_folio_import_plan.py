"""The dry run of an import (Folio 5.3): the plan, the author mapping, per-page problems."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.imports import FolioExternalRef, ImportSource, ImportStatus
from radicle.folio.db.models import FolioNode, FolioSpace, NodeKind
from radicle.folio.services import import_plan, imports, nodes
from radicle.platform.db.models import User
from radicle.platform.errors import Conflict, Forbidden, ValidationFailed
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


async def test_a_confluence_dry_run(db: AsyncSession, team: Team, space: FolioSpace) -> None:
    fernando, ana = await _user(db, "fernando"), await _user(db, "ana")
    item = await imports.create(
        db,
        fernando,
        space,
        source=ImportSource.confluence,
        filename="ENG.zip",
        data=zipped("confluence"),
    )
    assert item.status == ImportStatus.uploaded
    report = await import_plan.dry_run(db, fernando, item, {"authors": {"Ana López": "@ana"}})
    assert item.status == ImportStatus.checked and item.options["authors"]
    assert [(p["title"], p["action"]) for p in report["pages"]] == [
        ("Home", "create"),
        ("Guías", "create"),
        ("Conectar un agente", "create"),
        ("Decisiones", "create"),
    ]
    assert report["authors"] == [
        {"source": "Ana López", "user": {"id": str(ana.id), "handle": "ana", "name": "Ana"}},
        {"source": "fernando@example.com", "user": None},
    ]
    guide = report["pages"][2]
    assert guide["labels"] == ["mcp", "agentes"] and guide["attachments"] == 3
    assert guide["errors"] == ["Missing file: attachments/65541/99999.png"]
    assert report["totals"] == {
        "pages": 4,
        "folders": 0,
        "databases": 0,
        "attachments": 3,
        "updates": 0,
        "with_errors": 1,
    }


async def test_authors_match_by_email_and_pages_already_imported_are_updates(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, "fernando")
    files = "---\nauthor: luis@example.com\n---\n# Hola\n\nTexto."
    item = await imports.create(
        db, fernando, space, source=ImportSource.markdown, filename="hola.md", data=files.encode()
    )
    node = await nodes.create_node(db, fernando, space, kind=NodeKind.page, title="Hola")
    ref = FolioExternalRef(
        source=ImportSource.markdown, external_id="hola.md", space_id=space.id, node_id=node.id
    )
    db.add(ref)
    report = await import_plan.dry_run(db, fernando, item, {})
    assert report["authors"][0]["user"]["handle"] == "luis"
    assert report["pages"][0]["action"] == "update" and report["totals"]["updates"] == 1
    # A node in the trash doesn't count: importing again creates the page again.
    node.deleted_at = node.created_at
    report = await import_plan.dry_run(db, fernando, item, {})
    assert report["pages"][0]["action"] == "create"


async def test_wrong_uploads_options_and_people(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
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
        db, fernando, space, source=ImportSource.markdown, filename="a.png", data=b"png"
    )
    report = await import_plan.dry_run(db, fernando, item, {})
    assert report["errors"] == ["No Markdown files (.md) were found in the upload."]
    with pytest.raises(ValidationFailed, match="Unknown options: color"):
        await import_plan.dry_run(db, fernando, item, {"color": "red"})
    with pytest.raises(ValidationFailed, match="doesn't exist"):
        await import_plan.dry_run(db, fernando, item, {"authors": {"Ana": "nope"}})
    with pytest.raises(ValidationFailed, match="doesn't exist"):
        await import_plan.dry_run(db, fernando, item, {"authors": {"Ana": str(uuid.uuid4())}})
    with pytest.raises(ValidationFailed, match="Pick a page or folder"):
        await import_plan.dry_run(db, fernando, item, {"parent_id": str(uuid.uuid4())})
    with pytest.raises(Forbidden):
        await import_plan.dry_run(db, luis, item, {})
    with pytest.raises(Forbidden):
        await imports.get(db, luis, item.id)
    assert await imports.list_imports(db, luis) == []
    assert [i.id for i in await imports.list_imports(db, fernando)] == [item.id]
    item.status = ImportStatus.done
    with pytest.raises(Conflict, match="is done"):
        await import_plan.dry_run(db, fernando, item, {})


async def test_the_space_admin_of_one_space_only(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, "fernando")
    item = await imports.create(
        db, fernando, space, source=ImportSource.word, filename="x.docx", data=b"not a docx"
    )
    assert (await imports.get(db, fernando, item.id)).id == item.id
    report = await import_plan.dry_run(db, fernando, item, {})
    assert report["pages"][0]["errors"] == [
        "This file is not a valid .docx. Save it again from Word."
    ]
    folder = await db.scalar(select(FolioNode).where(FolioNode.space_id == space.id))
    assert folder is None  # a dry run creates nothing
