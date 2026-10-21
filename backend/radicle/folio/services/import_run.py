"""Running an import (Folio 5.3) in the worker: each page of the plan is created, or
updated when an earlier import made it, with its files uploaded as the page's assets.
Pages arrive as drafts; when the admin gave default metadata and a page's metadata is
then complete, it is published. One page failing doesn't stop the others."""

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.databases import FolioDbRow
from radicle.folio.db.imports import FolioExternalRef, FolioImport, ImportStatus
from radicle.folio.db.models import FolioNode, FolioSpace, NodeKind
from radicle.folio.services import (
    assets,
    databases,
    db_rows,
    drafts,
    import_plan,
    imports,
    nodes,
    publishing,
)
from radicle.folio.services.importing.model import Bundle, Page
from radicle.folio.services.metadata import MetadataIncomplete
from radicle.platform.db.models import AuditApp, User, utcnow
from radicle.platform.errors import Conflict, NotFound, ProblemError
from radicle.platform.services import audit, queue
from radicle.platform.storage import get_storage

RUN_JOB = "folio_import_run"
KINDS = {"page": NodeKind.page, "folder": NodeKind.folder, "database": NodeKind.database}
MAX_LABELS = 15


async def _space(db: AsyncSession, item: FolioImport) -> FolioSpace:
    space = await db.get(FolioSpace, item.target_space_id)
    if space is None or space.deleted_at is not None:
        raise NotFound("The import's space no longer exists.")
    return space


async def start(db: AsyncSession, user: User, item: FolioImport) -> FolioImport:
    space = await _space(db, item)
    await imports.require_import(db, user, space)
    if item.status != ImportStatus.checked:
        raise Conflict(
            f"This import is {item.status.value}. Run its dry run first "
            "(POST /imports/{id}/dry-run), check the plan, then run it.",
            code="import_not_checked",
        )
    item.status = ImportStatus.running
    item.stats = {"run_by": str(user.id)}
    audit.record(
        db,
        user,
        "folio.import_run",
        target_type="folio_space",
        target_id=space.id,
        app=AuditApp.folio,
        import_id=str(item.id),
        source=item.source.value,
        filename=item.filename,
        pages=len(item.report.get("pages", [])),
    )
    await queue.enqueue(
        db, RUN_JOB, queueing_lock=f"folio-import:{item.id}", import_id=str(item.id)
    )
    await db.flush()
    return item


def _metadata(page: Page, owner: str | None, default: dict[str, Any] | None) -> dict[str, Any]:
    meta: dict[str, Any] = dict(default or {})
    labels = [*(meta.get("labels") or []), *page.labels]
    meta["labels"] = list(dict.fromkeys(labels))[:MAX_LABELS]
    if owner:
        meta["owner"] = owner
    meta["title"] = page.title
    return meta


async def _files(
    db: AsyncSession, user: User, node: FolioNode, page: Page, found: Bundle, errors: list[str]
) -> str:
    """The page's Markdown with each `import:` ref pointing at an asset of the node."""
    ids: dict[str, uuid.UUID] = {}
    for ref in found.refs(page):
        file = found.attachments[ref]
        try:
            asset = await assets.upload(db, user, node, filename=file.name, data=file.data)
        except ProblemError as e:
            errors.append(f"{file.name}: {e.detail}")
            continue
        ids[ref] = asset.id
    lines = []
    for line in page.markdown.split("\n"):
        refs = re.findall(r"import:(a\d+)", line)
        if any(r not in ids for r in refs):
            continue  # a file that couldn't be uploaded
        lines.append(re.sub(r"import:(a\d+)", lambda m: f"{ids[m.group(1)]}", line))
    markdown = "\n".join(lines)
    return re.sub(r"\]\(([0-9a-f-]{36})\)", r"](asset:\1)", markdown)


async def _database(db: AsyncSession, user: User, node: FolioNode, page: Page) -> None:
    current = await databases.get_database(db, node)
    keys = {c["name"]: c["key"] for c in current.columns}
    columns = [
        {"name": name, "type": "text", **({"key": keys[name]} if name in keys else {})}
        for name in page.columns[: databases.MAX_COLUMNS]
    ]
    change = await databases.update_schema(db, user, node, columns=columns)
    for row in await db.scalars(
        select(FolioDbRow).where(FolioDbRow.node_id == node.id, FolioDbRow.deleted_at.is_(None))
    ):
        row.deleted_at = utcnow()  # importing again replaces the rows
    order = [c["key"] for c in change.database.columns]
    for row_values in page.rows:
        values = {k: v for k, v in zip(order, row_values, strict=False) if v.strip()}
        await db_rows.add_row(db, user, node, values)


async def _page(
    db: AsyncSession,
    user: User,
    item: FolioImport,
    space: FolioSpace,
    page: Page,
    *,
    found: Bundle,
    node: FolioNode | None,
    parent_id: uuid.UUID | None,
    owner: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"external_id": page.external_id, "title": page.title}
    errors = list(page.errors)
    if node is None:
        node = await nodes.create_node(
            db, user, space, kind=KINDS[page.kind], title=page.title, parent_id=parent_id
        )
        db.add(FolioExternalRef(source=item.source, external_id=page.external_id, node_id=node.id))
        result["action"] = "created"
    else:
        await nodes.update_node(db, user, node, nodes.NodeChanges(title=page.title))
        result["action"] = "updated"
    result["node_id"] = str(node.id)
    if node.kind == NodeKind.database:
        await _database(db, user, node, page)
    elif node.kind in (NodeKind.page, NodeKind.blog_post):
        markdown = await _files(db, user, node, page, found, errors)
        default = item.options.get("default_metadata")
        metadata = _metadata(page, owner, default)
        await drafts.save_draft(db, user, node, content_md=markdown, metadata=metadata)
        result["published"] = False
        if default:
            try:
                await publishing.publish(db, user, node, change_note="Imported", confirm=True)
                result["published"] = True
            except MetadataIncomplete as e:
                result["missing"] = [err["field"] for err in e.errors]
    result["errors"] = errors
    return result


async def apply(db: AsyncSession, user: User, item: FolioImport) -> dict[str, Any]:
    space = await _space(db, item)
    found = await imports.read_bundle(item)
    chosen = item.options.get("authors") or {}
    authors = await import_plan.resolve_authors(
        db, {p.author for p in found.pages if p.author}, chosen
    )
    before = await import_plan.existing_nodes(db, item.source, [p.external_id for p in found.pages])
    root = item.options.get("parent_id")
    made: dict[str, uuid.UUID] = {}
    results = []
    for page in found.pages:
        parent = made.get(page.parent_id) if page.parent_id else None
        person = authors.get(page.author) if page.author else None
        try:
            async with db.begin_nested():
                result = await _page(
                    db,
                    user,
                    item,
                    space,
                    page,
                    found=found,
                    node=before.get(page.external_id),
                    parent_id=parent or (uuid.UUID(root) if root else None),
                    owner=person.handle if person else None,
                )
        except ProblemError as e:
            result = {
                "external_id": page.external_id,
                "title": page.title,
                "action": "failed",
                "errors": [*page.errors, e.detail],
            }
        if "node_id" in result:
            made[page.external_id] = uuid.UUID(result["node_id"])
        results.append(result)
    return {
        "pages": results,
        "totals": {
            "created": sum(r["action"] == "created" for r in results),
            "updated": sum(r["action"] == "updated" for r in results),
            "failed": sum(r["action"] == "failed" for r in results),
            "published": sum(bool(r.get("published")) for r in results),
            "drafts": sum(r.get("published") is False for r in results),
        },
    }


@queue.handler(RUN_JOB)
async def run_import(db: AsyncSession, import_id: str, **_: Any) -> None:
    item = await db.get(FolioImport, uuid.UUID(import_id))
    if item is None or item.status != ImportStatus.running:
        return
    user = await db.get(User, uuid.UUID(item.stats["run_by"]))
    if user is None:
        item.status, item.finished_at = ImportStatus.failed, utcnow()
        item.stats = {**item.stats, "error": "The person who ran this import no longer exists."}
        return
    try:
        async with db.begin_nested():
            outcome = await apply(db, user, item)
    except Exception as e:  # report it on the import instead of retrying a broken upload
        item.status, item.finished_at = ImportStatus.failed, utcnow()
        item.stats = {**item.stats, "error": f"The import stopped: {e}"}
        return
    item.report = {**item.report, "run": outcome["pages"]}
    item.stats = {**item.stats, **outcome["totals"]}
    item.status, item.finished_at = ImportStatus.done, utcnow()
    try:
        await get_storage().delete(item.upload_key)  # the pages hold everything now
    except OSError:
        pass
