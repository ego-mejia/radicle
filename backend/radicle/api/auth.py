from fastapi import APIRouter, Request, Response

from radicle.api.deps import (
    AppSettings,
    CurrentPrincipal,
    Db,
    clear_session_cookies,
    set_session_cookies,
)
from radicle.api.me import me_out
from radicle.api.ratelimit import login_limiter
from radicle.api.schemas.users import LoginIn, MeOut
from radicle.core.errors import ValidationFailed
from radicle.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=MeOut)
async def login(
    body: LoginIn, request: Request, response: Response, db: Db, settings: AppSettings
) -> MeOut:
    """Sign in with email and password. Agents cannot sign in; they use API tokens."""
    ip = request.client.host if request.client else "unknown"
    login_limiter.hit(ip, settings.login_rate_limit_per_minute)
    user = await auth.authenticate_password(db, str(body.email), body.password)
    issued = await auth.create_session(
        db,
        user,
        days=settings.session_days,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    set_session_cookies(response, issued.token, settings)
    return await me_out(db, user)


@router.post("/logout", status_code=204)
async def logout(principal: CurrentPrincipal, response: Response, db: Db) -> Response:
    if principal.session_token is None:
        raise ValidationFailed(
            "Logout only applies to browser sessions; revoke tokens instead.", code="not_a_session"
        )
    await auth.delete_session(db, principal.session_token)
    response.status_code = 204
    clear_session_cookies(response)
    return response
