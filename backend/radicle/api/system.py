from fastapi import APIRouter, Request, Response
from pydantic import Field
from sqlalchemy import text

from radicle import __version__
from radicle.api.deps import AppSettings, Db, set_session_cookies
from radicle.api.schemas.common import Output
from radicle.api.schemas.users import Health, SetupIn, SetupStatus, UserOut, Version
from radicle.platform.errors import ProblemError
from radicle.platform.services import audit, auth, images, users

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health)
async def health(db: Db) -> Health:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ProblemError("Database is unreachable.", status=503, code="db_unavailable") from exc
    return Health(status="ok", database="ok")


@router.get("/version", response_model=Version)
async def version() -> Version:
    return Version(version=__version__, api_version="v1")


class Limits(Output):
    max_upload_mb: int
    image_default_resize: str = Field(description="original, large, medium or small")
    image_presets: dict[str, int | None] = Field(description="Longest side in pixels")


@router.get("/limits", response_model=Limits)
async def limits(settings: AppSettings) -> Limits:
    """Upload limits, so clients can check before sending."""
    return Limits(
        max_upload_mb=settings.max_upload_mb,
        image_default_resize=settings.image_default_resize,
        image_presets=images.PRESETS,
    )


@router.get("/setup/status", response_model=SetupStatus)
async def setup_status(db: Db) -> SetupStatus:
    return SetupStatus(needs_setup=await users.needs_setup(db))


@router.post("/setup", response_model=UserOut, status_code=201)
async def setup(
    body: SetupIn, request: Request, response: Response, db: Db, settings: AppSettings
) -> UserOut:
    """Create the first instance admin and sign them in. Only works once."""
    user = await users.create_first_admin(
        db,
        handle=body.handle,
        display_name=body.display_name,
        email=str(body.email),
        password=body.password,
    )
    audit.record(
        db, user, "user.create", target_type="user", target_id=user.handle, first_admin=True
    )
    audit.record(db, user, "user.make_admin", target_type="user", target_id=user.handle)
    issued = await auth.create_session(
        db,
        user,
        days=settings.session_days,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    set_session_cookies(response, issued.token, settings)
    return UserOut.model_validate(user)
