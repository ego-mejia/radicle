"""Link previews over REST (Folio 3.7): GET /api/v1/folio/link-preview?url=."""

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.services import link_preview
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output

router = APIRouter(tags=["folio"])


class LinkPreviewOut(Output):
    url: str
    title: str
    description: str
    site_name: str
    icon_url: str | None
    image_url: str | None
    provider: str | None = Field(description="youtube, figma, loom, google_docs or github")
    embed_url: str | None = Field(description="An iframe URL, only for those providers")


@router.get("/link-preview", response_model=LinkPreviewOut)
async def get_link_preview(
    principal: CurrentPrincipal,
    db: Db,
    url: str = Query(min_length=8, max_length=2000, description="An http or https link"),
) -> LinkPreviewOut:
    """A card for a pasted link, cached 24 hours. Private and internal addresses are
    refused."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    p = await link_preview.preview(db, url)
    return LinkPreviewOut(
        url=p.url,
        title=p.title,
        description=p.description,
        site_name=p.site_name,
        icon_url=p.icon_url,
        image_url=p.image_url,
        provider=p.provider,
        embed_url=p.embed_url,
    )
