"""Running imports (Folio 5.3). Acceptance: a Confluence space comes in with its tree,
attachments and labels; importing it again doesn't duplicate anything."""

import io
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.databases import FolioDbRow
from radicle.folio.db.imports import FolioImport, ImportSource, ImportStatus
from radicle.folio.db.models import FolioAsset, FolioDraft, FolioNode, FolioSpace, NodeKind
from radicle.folio.services import import_plan, import_run, imports, nodes
from radicle.platform.db.models import AuditEntry, User
from radicle.platform.errors import Conflict, Forbidden
from tests.conftest import Team, run_jobs
from tests.folio_import_fixtures import zipped
from tests.integration.folio_helpers import API, METADATA


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


async def _import(
    db: AsyncSession,
    user: User,
    space: FolioSpace,
    source: ImportSource,
    filename: str,
    data: bytes,
    options: dict[str, object] | None = None,
) -> FolioImport:
    item = await imports.create(db, user, space, source=source, filename=filename, data=data)
    await import_plan.dry_run(db, user, item, options or {})
    await import_run.start(db, user, item)
    assert import_run.RUN_JOB in await run_jobs(db)
    await db.refresh(item)
    return item


async def _titles(db: AsyncSession, space: FolioSpace) -> list[tuple[str, str | None]]:
    rows = list(
        await db.scalars(
            select(FolioNode).where(FolioNode.space_id == space.id, FolioNode.deleted_at.is_(None))
        )
    )
    by_id = {n.id: n.title for n in rows}
    return sorted((n.title, by_id.get(n.parent_id) if n.parent_id else None) for n in rows)


async def test_acceptance_a_confluence_space_comes_in_once(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando, ana = await _user(db, "fernando"), await _user(db, "ana")
    options = {"authors": {"Ana López": str(ana.id)}}
    item = await _import(
        db, fernando, space, ImportSource.confluence, "ENG.zip", zipped("confluence"), options
    )
    assert item.status == ImportStatus.done and item.finished_at is not None
    assert item.stats["created"] == 4 and item.stats["drafts"] == 4
    assert await _titles(db, space) == [
        ("Conectar un agente", "Guías"),
        ("Decisiones", "Home"),
        ("Guías", "Home"),
        ("Home", None),
    ]
    guide = await db.scalar(select(FolioNode).where(FolioNode.title == "Conectar un agente"))
    assert guide is not None
    draft = await db.get(FolioDraft, guide.id)
    assert draft is not None
    assert draft.metadata_["labels"] == ["mcp", "agentes"] and draft.metadata_["owner"] == "ana"
    files = list(await db.scalars(select(FolioAsset).where(FolioAsset.node_id == guide.id)))
    assert sorted(f.filename for f in files) == ["flow.png", "notas.txt", "spec.pdf"]
    types = [b["type"] for b in draft.content_json["content"]]
    assert "image" in types and types.count("file") == 2
    image = next(b for b in draft.content_json["content"] if b["type"] == "image")
    assert image["attrs"]["assetId"] in {str(f.id) for f in files}
    audit = await db.scalar(select(AuditEntry).where(AuditEntry.action == "folio.import_run"))
    assert audit is not None and audit.details["source"] == "confluence"

    again = await _import(
        db, fernando, space, ImportSource.confluence, "ENG.zip", zipped("confluence"), options
    )
    assert again.stats["created"] == 0 and again.stats["updated"] == 4
    assert len(await _titles(db, space)) == 4


async def test_complete_pages_are_published_and_databases_get_rows(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, "fernando")
    notion = {
        "Guia 11112222333344445555666677778888.md": "# Guia\n\nTags: mcp\n\nHola.",
        "Tools 99998888777766665555444433332222.csv": "Name,Status\nCursor,En uso\nZed,\n",
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, content in notion.items():
            z.writestr(name, content)
    default = {k: v for k, v in METADATA.items() if k != "labels"}
    item = await _import(
        db,
        fernando,
        space,
        ImportSource.notion,
        "notion.zip",
        out.getvalue(),
        {"default_metadata": default},
    )
    assert item.stats["published"] == 1 and item.stats["created"] == 2
    page = await db.scalar(select(FolioNode).where(FolioNode.title == "Guia"))
    assert page is not None and page.published_version_id is not None
    table = await db.scalar(select(FolioNode).where(FolioNode.kind == NodeKind.database))
    assert table is not None and table.title == "Tools"
    rows = list(await db.scalars(select(FolioDbRow).where(FolioDbRow.node_id == table.id)))
    assert sorted(r.values.get("name") for r in rows) == ["Cursor", "Zed"]
    # Importing again replaces the rows instead of adding them twice.
    await _import(db, fernando, space, ImportSource.notion, "notion.zip", out.getvalue())
    live = await db.scalar(
        select(func.count())
        .select_from(FolioDbRow)
        .where(FolioDbRow.node_id == table.id, FolioDbRow.deleted_at.is_(None))
    )
    assert live == 2


async def test_incomplete_metadata_stays_a_draft_and_a_bad_page_fails_alone(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando = await _user(db, "fernando")
    parent = await nodes.create_node(db, fernando, space, kind=NodeKind.folder, title="Viejo")
    item = await _import(
        db,
        fernando,
        space,
        ImportSource.markdown,
        "a.md",
        b"# Corta\n\nSin descripcion.",
        {"default_metadata": {"doc_type": "how-to"}, "parent_id": str(parent.id)},
    )
    result = item.report["run"][0]
    assert result["published"] is False and "description" in result["missing"]
    node = await db.get(FolioNode, result["node_id"])
    assert node is not None and node.parent_id == parent.id


async def test_running_needs_a_dry_run_and_a_space_admin(
    db: AsyncSession, team: Team, space: FolioSpace
) -> None:
    fernando, luis = await _user(db, "fernando"), await _user(db, "luis")
    item = await imports.create(
        db, fernando, space, source=ImportSource.markdown, filename="a.md", data=b"# A"
    )
    with pytest.raises(Conflict, match="Run its dry run first"):
        await import_run.start(db, fernando, item)
    await import_plan.dry_run(db, fernando, item, {})
    with pytest.raises(Forbidden):
        await import_run.start(db, luis, item)
    await import_run.start(db, fernando, item)
    with pytest.raises(Conflict, match="is running"):
        await import_run.start(db, fernando, item)
    # The worker skips an import that isn't running any more.
    item.status = ImportStatus.failed
    await import_run.run_import(db, str(item.id))
    assert item.finished_at is None
