"""Exports over REST (Folio 5.2): ask for one, follow its progress, download it."""

import uuid
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.folio.db.exports import ExportFormat, FolioExport
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import audit_log, exports, nodes, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.errors import ValidationFailed

router = APIRouter(tags=["folio"])

Format = Literal["pdf", "docx", "html", "markdown"]


class ExportOut(Output):
    id: uuid.UUID
    format: Format
    scope: Literal["node", "space"]
    node_id: uuid.UUID | None
    status: Literal["queued", "running", "done", "failed"]
    filename: str | None
    stats: dict[str, Any] = Field(description="pages and bytes when done; error when it failed")
    download_url: str | None = Field(description="Once it is done")
    created_at: UtcDatetime
    finished_at: UtcDatetime | None


class ExportsOut(Output):
    items: list[ExportOut]


class ExportIn(Input):
    node: uuid.UUID | None = Field(default=None, description="A published page or post")
    space: str | None = Field(default=None, description="Space key, for the whole space")
    format: Format


def _out(row: FolioExport) -> ExportOut:
    done = row.status.value == "done"
    return ExportOut(
        id=row.id,
        format=row.format.value,
        scope=row.scope.value,
        node_id=row.node_id,
        status=row.status.value,
        filename=row.filename,
        stats=row.stats,
        download_url=f"/api/v1/folio/exports/{row.id}/download" if done else None,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.post("/exports", response_model=ExportOut, status_code=202)
async def create_export(body: ExportIn, principal: CurrentPrincipal, db: Db) -> ExportOut:
    """Queue an export of a page or a space; poll it until it is done, then download it.
    Needs the space's export permission."""
    await _reader(db, principal)
    target: FolioNode | FolioSpace
    if body.node is not None and body.space is None:
        target = await nodes.get_node(db, principal.user, body.node)
    elif body.space is not None and body.node is None:
        target = await spaces.get_space(db, principal.user, body.space)
    else:
        raise ValidationFailed(
            "Send either node (a page id) or space (a space key).",
            errors=[{"field": "node", "message": "one of node or space"}],
        )
    row = await exports.create_export(db, principal.user, target, ExportFormat(body.format))
    audit_log.record(
        db,
        principal.user,
        "export_create",
        target_type="folio_node" if row.node_id else "folio_space",
        target_id=row.node_id or row.space_id,
        after={"export": str(row.id), "format": row.format.value},
    )
    return _out(row)


@router.get("/exports", response_model=ExportsOut)
async def list_exports(principal: CurrentPrincipal, db: Db) -> ExportsOut:
    """Your latest exports, newest first."""
    await _reader(db, principal)
    return ExportsOut(items=[_out(r) for r in await exports.list_exports(db, principal.user)])


@router.get("/exports/{export_id}", response_model=ExportOut)
async def get_export(export_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> ExportOut:
    """Its progress. Only its author sees it."""
    await _reader(db, principal)
    return _out(await exports.get_export(db, principal.user, export_id))


@router.get("/exports/{export_id}/download", response_class=Response)
async def download_export(export_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """The file, once the export is done."""
    await _reader(db, principal)
    row, data = await exports.download(db, principal.user, export_id)
    mime = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(row.format.value, "application/zip")
    name = quote(row.filename or "export")
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{name}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
