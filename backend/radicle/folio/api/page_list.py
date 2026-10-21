"""The "list by label" block over REST (Folio 3.4): GET /api/v1/folio/page-list."""

from fastapi import APIRouter, Query

from radicle.folio.api.spaces import NodeRef, _ref
from radicle.folio.services import page_list
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, UtcDatetime

router = APIRouter(tags=["folio"])


class ListedPageOut(NodeRef):
    space: str
    published_at: UtcDatetime | None


class PageListOut(Output):
    items: list[ListedPageOut]


@router.get("/page-list", response_model=PageListOut)
async def get_page_list(
    principal: CurrentPrincipal,
    db: Db,
    label: str = Query(min_length=1, max_length=50, description="e.g. onboarding"),
    space: str | None = Query(default=None, description="Only this space's pages"),
    limit: int = Query(default=10, ge=1, le=page_list.MAX_LIMIT),
) -> PageListOut:
    """Published pages with the label that you can see, newest first."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    found = await page_list.pages_with_label(db, principal.user, label, space=space, limit=limit)
    return PageListOut(
        items=[
            ListedPageOut(
                **_ref(p.node).model_dump(), space=p.space, published_at=p.node.published_at
            )
            for p in found
        ]
    )
