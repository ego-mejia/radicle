from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from radicle import __version__
from radicle.docket.api import (
    assistant,
    attachments,
    audit,
    auth,
    boards,
    bulk,
    dashboards,
    discussion,
    fields,
    groups,
    inbox,
    jobs,
    me,
    planning,
    projects,
    reports,
    screens,
    search,
    security,
    sprints,
    sso,
    system,
    templates,
    tickets,
    time,
    timeline,
    users,
    work,
)
from radicle.docket.core import mcp_catalog
from radicle.docket.core.authz import DocketAuthz
from radicle.docket.mcp import server as mcp_server
from radicle.docket.public.router import router as public_router
from radicle.folio.api.router import router as folio_router
from radicle.folio.authz import FolioAuthz
from radicle.folio.mcp import catalog as folio_catalog
from radicle.folio.mcp import server as folio_mcp
from radicle.folio.services import collab
from radicle.platform import authz, mcp_tools
from radicle.platform.api import ai as ai_api
from radicle.platform.api import notifications as notifications_api
from radicle.platform.api import webhooks as webhooks_api
from radicle.platform.config import get_settings
from radicle.platform.crypto import require_key
from radicle.platform.db.session import dispose_engine
from radicle.platform.errors import NotFound, install_error_handlers
from radicle.platform.services.audit import RequestInfoMiddleware
from radicle.platform.services.notify_hub import hub as notify_hub

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with (
        mcp_server.server.session_manager.run(),
        folio_mcp.server.session_manager.run(),
    ):
        yield
    await collab.rooms.close_all()
    await notify_hub.close()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    require_key()  # no secret key, no app: secrets in the database depend on it
    mcp_tools.register(mcp_catalog.CATALOG, mcp_server.server)
    mcp_tools.register(folio_catalog.CATALOG, folio_mcp.server)
    authz.register(DocketAuthz())
    authz.register(FolioAuthz())
    app = FastAPI(
        title="Radicle",
        version=__version__,
        description="Open source, self-hosted ticket tracker with a built-in MCP server.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    install_error_handlers(app)
    # The audit log records where each action came from.
    app.add_middleware(RequestInfoMiddleware)

    api = APIRouter(prefix=API_PREFIX)
    # search goes before tickets so GET /tickets is not shadowed by /tickets/{key}.
    for module in (
        system,
        auth,
        me,
        users,
        projects,
        planning,
        bulk,
        work,
        boards,
        sprints,
        fields,
        screens,
        search,
        tickets,
        discussion,
        jobs,
        templates,
        attachments,
        time,
        timeline,
        reports,
        dashboards,
        groups,
        security,
        inbox,
        sso,
        assistant,
        audit,
        ai_api,
        notifications_api,
        webhooks_api,
    ):
        api.include_router(module.router)
    api.include_router(folio_router)
    app.include_router(api)
    app.include_router(public_router)
    mcp_server.mount(app)
    folio_mcp.mount(app)
    # Unversioned alias for container health checks and load balancers.
    app.add_api_route("/health", system.health, methods=["GET"], include_in_schema=False)

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    async def api_not_found(path: str) -> None:
        raise NotFound(f"No API route /api/{path}. See /api/docs for the available endpoints.")

    if settings.static_dir and Path(settings.static_dir, "index.html").is_file():
        _mount_spa(app, Path(settings.static_dir))
    return app


def _mount_spa(app: FastAPI, root: Path) -> None:
    root = root.resolve()
    index = root / "index.html"
    if (root / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
