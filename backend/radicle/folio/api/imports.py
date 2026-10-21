"""Imports over REST (Folio 5.3): upload an export into a space, dry-run it with the
author mapping, then run it in the worker. Only the space's admins import into it."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import Field

from radicle.folio.api.assets import _read_limited
from radicle.folio.db.imports import FolioImport, ImportSource
from radicle.folio.db.models import FolioSpace
from radicle.folio.services import import_plan, import_run, imports, spaces
from radicle.folio.services.importing import bundle
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime

router = APIRouter(tags=["folio"])
Source = Literal["confluence", "notion", "word", "markdown"]


class ImportOut(Output):
    id: uuid.UUID
    source: Source
    space: str = Field(description="Key of the space it imports into")
    filename: str
    status: Literal["uploaded", "checked", "running", "done", "failed"]
    options: dict[str, Any]
    report: dict[str, Any] = Field(
        description="The dry run's plan (pages, authors, errors, totals), and `run` with "
        "each page's outcome once it ran"
    )
    stats: dict[str, Any]
    created_at: UtcDatetime
    finished_at: UtcDatetime | None


class ImportOptionsIn(Input):
    authors: dict[str, str | None] | None = Field(
        None, description="Each source author (as the plan lists them) → a user id, or null"
    )
    default_metadata: dict[str, Any] | None = Field(
        None, description="Metadata for every page; a page that's then complete is published"
    )
    parent_id: uuid.UUID | None = Field(None, description="Import under this page or folder")


async def _out(db: Db, item: FolioImport) -> ImportOut:
    space = await db.get(FolioSpace, item.target_space_id)
    return ImportOut(
        id=item.id,
        source=item.source.value,
        space=space.key if space else "",
        filename=item.filename,
        status=item.status.value,
        options=item.options,
        report=item.report,
        stats={k: v for k, v in item.stats.items() if k != "run_by"},
        created_at=item.created_at,
        finished_at=item.finished_at,
    )


@router.post("/imports", response_model=ImportOut, status_code=201)
async def create_import(
    file: Annotated[UploadFile, File(description="The export: a zip, a .docx or a .md")],
    source: Annotated[Source, Form(description="Where the export comes from")],
    space: Annotated[str, Form(description="Key of the space to import into")],
    principal: CurrentPrincipal,
    db: Db,
) -> ImportOut:
    """Upload an export. Nothing is created until it's dry-run and run."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    target = await spaces.get_space(db, principal.user, space)
    data = await _read_limited(file, bundle.MAX_UPLOAD)
    item = await imports.create(
        db,
        principal.user,
        target,
        source=ImportSource(source),
        filename=file.filename or "upload",
        data=data,
    )
    return await _out(db, item)


@router.get("/imports", response_model=Page[ImportOut])
async def list_imports(principal: CurrentPrincipal, db: Db) -> Page[ImportOut]:
    """Imports into the spaces you administer, newest first."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    items = await imports.list_imports(db, principal.user)
    return Page[ImportOut](items=[await _out(db, i) for i in items])


@router.get("/imports/{import_id}", response_model=ImportOut)
async def get_import(import_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> ImportOut:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    return await _out(db, await imports.get(db, principal.user, import_id))


@router.post("/imports/{import_id}/dry-run", response_model=ImportOut)
async def dry_run(
    import_id: uuid.UUID, body: ImportOptionsIn, principal: CurrentPrincipal, db: Db
) -> ImportOut:
    """The plan: each page created or updated, who each author becomes, files and problems.
    Send it again with other options as often as needed; it creates nothing."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    item = await imports.get(db, principal.user, import_id)
    options = body.model_dump(exclude_none=True, mode="json")
    await import_plan.dry_run(db, principal.user, item, options)
    return await _out(db, item)


@router.post("/imports/{import_id}/run", response_model=ImportOut, status_code=202)
async def run(import_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> ImportOut:
    """Run the checked import in the background; GET it to follow its status."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    item = await imports.get(db, principal.user, import_id)
    await import_run.start(db, principal.user, item)
    return await _out(db, item)
