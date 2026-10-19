from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from radicle import __version__
from radicle.api import (
    attachments,
    auth,
    bulk,
    discussion,
    fields,
    jobs,
    me,
    planning,
    projects,
    screens,
    search,
    system,
    templates,
    tickets,
    time,
    users,
    work,
)
from radicle.core.config import get_settings
from radicle.core.errors import NotFound, install_error_handlers
from radicle.db.session import dispose_engine
from radicle.mcp import server as mcp_server

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp_server.server.session_manager.run():
        yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
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
        fields,
        screens,
        search,
        tickets,
        discussion,
        jobs,
        templates,
        attachments,
        time,
    ):
        api.include_router(module.router)
    app.include_router(api)
    mcp_server.mount(app)
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
