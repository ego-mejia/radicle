"""The public page's HTML at /pub/{token} (Folio 5.1): the app's index with the right
status and headers, so a revoked link is a real 404 and `noindex` reaches crawlers that
never run JavaScript. The page itself reads /api/v1/folio/pub/{token}."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from radicle.folio.services import public_links
from radicle.platform.api.deps import Db
from radicle.platform.config import get_settings
from radicle.platform.errors import NotFound

router = APIRouter(include_in_schema=False)
FALLBACK = "<!doctype html><title>Radicle</title><div id=root></div>"


@router.get("/pub/{token}", response_class=HTMLResponse)
@router.get("/pub/{token}/{rest:path}", response_class=HTMLResponse)
async def public_page(token: str, db: Db, rest: str = "") -> HTMLResponse:
    try:
        link, _, _ = await public_links.resolve(db, token)
    except NotFound:
        link = None
    static = get_settings().static_dir
    index = Path(static, "index.html") if static else None
    html = index.read_text() if index and index.is_file() else FALLBACK
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if link is None or link.noindex:
        headers["X-Robots-Tag"] = "noindex, nofollow"
    return HTMLResponse(html, status_code=200 if link else 404, headers=headers)
