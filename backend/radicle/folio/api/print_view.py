"""The print view's data (Folio 5.2): what the worker's browser reads to print a PDF, with
a signed, short-lived token instead of an account."""

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from pydantic import Field

from radicle.folio.api.public_links import PublicNodeOut, PublicPageOut, PublicSpaceOut
from radicle.folio.services import assets, exports
from radicle.folio.services.exporting.pages import owned_asset
from radicle.platform.api.deps import Db
from radicle.platform.api.schemas import Output
from radicle.platform.errors import NotFound
from radicle.platform.storage import get_storage

router = APIRouter(tags=["folio"])


class PrintOut(Output):
    space: PublicSpaceOut
    pages: list[PublicPageOut] = Field(description="In tree order, as the export's author sees")


def _node(n: object) -> PublicNodeOut:
    return PublicNodeOut.model_validate(n, from_attributes=True)


@router.get("/print/{token}", response_model=PrintOut)
async def read_print(token: str, db: Db) -> PrintOut:
    """The pages of an export being printed. The token comes with the export's job."""
    _, space, pages = await exports.print_view(db, token)
    out = []
    for p in pages:
        n, v = p.node, p.version
        children = [_node(c.node) for c in pages if c.node.parent_id == n.id]
        out.append(
            PublicPageOut(
                id=n.id,
                kind=n.kind.value,
                title=n.title,
                slug=n.slug,
                icon=n.icon,
                parent_id=n.parent_id,
                cover_asset_id=n.cover_asset_id,
                published_at=n.published_at,
                version=v.number,
                metadata=v.metadata_,
                content_json=v.content_json,
                children=children,
            )
        )
    return PrintOut(
        space=PublicSpaceOut(
            name=space.name,
            description=space.description,
            icon=space.icon,
            cover_asset_id=space.cover_asset_id,
        ),
        pages=out,
    )


@router.get("/print/{token}/assets/{asset_id}", response_class=Response)
async def read_print_asset(token: str, asset_id: uuid.UUID, db: Db) -> Response:
    _, _, pages = await exports.print_view(db, token)
    asset = await owned_asset(db, pages, str(asset_id))
    if asset is None:
        raise NotFound("No such file in this export.")
    inline = asset.mime_type in assets.INLINE_TYPES
    url = await get_storage().download_url(asset.storage_key, asset.filename, inline=inline)
    if url is not None:
        return RedirectResponse(url, status_code=302)
    return Response(
        content=await get_storage().get(asset.storage_key),
        media_type=asset.mime_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(asset.filename)}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
