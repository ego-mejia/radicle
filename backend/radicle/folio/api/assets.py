"""Folio assets over REST (Folio 1.2): upload to a page, then show or download."""

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import Field

from radicle.folio.db.models import FolioAsset
from radicle.folio.services import assets, nodes
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, UtcDatetime
from radicle.platform.storage import get_storage

router = APIRouter(tags=["folio"])
CHUNK = 1024 * 1024


class AssetOut(Output):
    id: uuid.UUID
    url: str = Field(description="Where to show or download it")
    filename: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    created_at: UtcDatetime


def _out(a: FolioAsset) -> AssetOut:
    return AssetOut(
        id=a.id,
        url=f"/api/v1/folio/assets/{a.id}",
        filename=a.filename,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        width=a.width,
        height=a.height,
        created_at=a.created_at,
    )


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(CHUNK):
        size += len(chunk)
        chunks.append(chunk)
        if size > limit:
            break
    return b"".join(chunks)


@router.post("/nodes/{node_id}/assets", response_model=AssetOut, status_code=201)
async def upload_asset(
    node_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="The file")],
    principal: CurrentPrincipal,
    db: Db,
    resize: Annotated[
        str | None, Form(description="Images: original, large, medium or small")
    ] = None,
) -> AssetOut:
    """Upload an image, file or video to a page. Images lose EXIF and shrink to `resize`."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    data = await _read_limited(file, assets.max_bytes())
    asset = await assets.upload(
        db, principal.user, node, filename=file.filename or "file", data=data, resize=resize
    )
    return _out(asset)


@router.get("/assets/{asset_id}", response_class=Response)
async def get_asset(asset_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    """The bytes, shown inline for images, PDFs and video and downloaded otherwise."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    asset = await assets.load(db, principal.user, asset_id)
    inline = asset.mime_type in assets.INLINE_TYPES
    url = await get_storage().download_url(asset.storage_key, asset.filename, inline=inline)
    if url is not None:
        return RedirectResponse(url, status_code=302)
    data = await get_storage().get(asset.storage_key)
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=asset.mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(asset.filename)}",
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )
