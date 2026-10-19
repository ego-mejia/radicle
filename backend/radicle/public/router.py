"""Server-rendered public pages of the inbox: /b/{slug}. Separate from the SPA so they load
fast and expose nothing of the app."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.datastructures import UploadFile

from radicle.api.deps import Db
from radicle.api.ratelimit import SlidingWindowLimiter
from radicle.core.errors import NotFound, RateLimited
from radicle.public.texts import TEXTS, pick_language
from radicle.services import altcha, public_form

router = APIRouter(include_in_schema=False)
templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)
tracking_limiter = SlidingWindowLimiter(window_seconds=60)
TRACKING_PER_MINUTE = 20


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _paragraphs(text: str) -> list[str]:
    """Admin texts are shown as plain paragraphs (escaped by the template)."""
    return [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]


def _render(name: str, request: Request, status: int = 200, **ctx: Any) -> HTMLResponse:
    lang = pick_language(request.headers.get("accept-language"))
    html = templates.get_template(name).render(lang=lang, t=TEXTS[lang], **ctx)
    return HTMLResponse(
        html,
        status_code=status,
        headers={
            "Content-Security-Policy": (
                "default-src 'self'; style-src 'unsafe-inline'; script-src 'self' "
                "'unsafe-inline' https://challenges.cloudflare.com https://js.hcaptcha.com; "
                "frame-src https://challenges.cloudflare.com https://*.hcaptcha.com; "
                "img-src 'self' data:; connect-src 'self' https://*.hcaptcha.com; "
                "frame-ancestors 'none'"
            ),
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        },
    )


def _not_found(request: Request) -> HTMLResponse:
    return _render("notfound.html", request, 404, project_name="", page_title="")


async def _form_context(project: Any, row: Any, slug: str) -> dict[str, Any]:
    return {
        "project_name": project.name,
        "page_title": row.title or project.name,
        "intro": _paragraphs(row.intro_md),
        "kinds": list(row.allowed_classifications),
        "require_email": row.require_email,
        "allow_attachments": row.allow_attachments,
        "max_attachments": row.max_attachments,
        "captcha": row.captcha.value,
        "site_key": (row.captcha_config or {}).get("site_key", ""),
        "token": public_form.form_token(row.public_slug),
        "base": f"/b/{slug}",
    }


@router.get("/b/{slug}", response_class=HTMLResponse)
async def form(slug: str, request: Request, db: Db) -> HTMLResponse:
    try:
        project, row = await public_form.load_form(db, slug)
    except NotFound:
        return _not_found(request)
    ctx = await _form_context(project, row, slug)
    return _render("form.html", request, values={}, errors={}, rejected=None, **ctx)


@router.get("/b/{slug}/challenge")
async def challenge(slug: str, db: Db) -> Response:
    try:
        await public_form.load_form(db, slug)
    except NotFound:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return JSONResponse(altcha.create_challenge(), headers={"Cache-Control": "no-store"})


@router.post("/b/{slug}", response_class=HTMLResponse)
async def send(slug: str, request: Request, db: Db) -> HTMLResponse:
    try:
        project, row = await public_form.load_form(db, slug)
    except NotFound:
        return _not_found(request)
    data = await request.form()
    files = []
    for item in data.getlist("files"):
        if isinstance(item, UploadFile) and item.filename:
            content = await item.read(public_form.MAX_FILE + 1)
            if content:
                files.append((item.filename, content))
    values = {
        k: str(data.get(k) or "")
        for k in ("classification", "title", "description", "name", "email")
    }
    sub = public_form.Submission(
        classification=values["classification"],
        title=values["title"],
        description=values["description"],
        name=values["name"] or None,
        email=values["email"] or None,
        honeypot=str(data.get("website") or "") or None,
        token=str(data.get("token") or ""),
        captcha=str(data.get("altcha") or data.get("h-captcha-response") or "") or None,
        files=files,
    )
    ctx = await _form_context(project, row, slug)
    try:
        ticket = await public_form.submit(db, project, row, sub, _ip(request))
    except public_form.Invalid as exc:
        return _render(
            "form.html", request, 422, values=values, errors=exc.errors, rejected=None, **ctx
        )
    except public_form.Rejected as exc:
        await db.rollback()
        return _render(
            "form.html", request, 422, values=values, errors={}, rejected=exc.detail, **ctx
        )
    await db.commit()
    return _render(
        "thanks.html",
        request,
        201,
        project_name=project.name,
        page_title=row.title or project.name,
        thank_you=_paragraphs(row.thank_you_md),
        code=ticket.tracking_code,
        base=f"/b/{slug}",
    )


@router.get("/b/{slug}/t", response_class=HTMLResponse)
async def lookup(slug: str, request: Request, db: Db, code: str | None = None) -> Response:
    if code:
        return RedirectResponse(f"/b/{slug}/t/{code.strip().upper()}", status_code=303)
    try:
        project, _ = await public_form.load_form(db, slug)
    except NotFound:
        return _not_found(request)
    return _render(
        "tracking.html",
        request,
        project_name=project.name,
        page_title="",
        item=None,
        unknown=False,
        base=f"/b/{slug}",
    )


@router.get("/b/{slug}/t/{code}", response_class=HTMLResponse)
async def track(slug: str, code: str, request: Request, db: Db) -> HTMLResponse:
    try:
        tracking_limiter.hit(f"track:{_ip(request)}", TRACKING_PER_MINUTE)
    except RateLimited as exc:
        return HTMLResponse(exc.detail, status_code=429, headers=exc.headers)
    try:
        project, row = await public_form.load_form(db, slug)
    except NotFound:
        return _not_found(request)
    try:
        item = await public_form.tracking(db, row, code)
    except NotFound:
        return _render(
            "tracking.html",
            request,
            404,
            project_name=project.name,
            page_title="",
            item=None,
            unknown=True,
            base=f"/b/{slug}",
        )
    return _render(
        "tracking.html",
        request,
        project_name=project.name,
        page_title="",
        item=item,
        unknown=False,
        base=f"/b/{slug}",
    )
