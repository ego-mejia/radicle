from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform import security
from radicle.platform.config import Settings, get_settings
from radicle.platform.db.models import User
from radicle.platform.db.session import get_db
from radicle.platform.errors import Forbidden, Unauthorized
from radicle.platform.services import auth

SESSION_COOKIE = "radicle_session"
CSRF_COOKIE = "radicle_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# "function" scope commits before the response is sent, so commit errors reach the client.
Db = Annotated[AsyncSession, Depends(get_db, scope="function")]
AppSettings = Annotated[Settings, Depends(get_settings)]


def set_session_cookies(response: Response, token: str, settings: Settings) -> None:
    max_age = settings.session_days * 86400
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    # Readable by the SPA so it can echo it back in the X-CSRF-Token header.
    response.set_cookie(
        CSRF_COOKIE,
        security.csrf_token_for(token),
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


async def get_principal(
    request: Request, response: Response, db: Db, settings: AppSettings
) -> auth.Principal:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials.strip():
            raise Unauthorized("Use 'Authorization: Bearer rdc_...'.", code="invalid_token")
        user = await auth.resolve_api_token(db, credentials.strip())
        return auth.Principal(user=user, via="token")

    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise Unauthorized("Sign in or send an API token.", code="not_authenticated")
    session = await auth.resolve_session(db, cookie, days=settings.session_days)
    if session is None:
        clear_session_cookies(response)
        raise Unauthorized("Your session expired. Sign in again.", code="session_expired")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not security.tokens_match(sent, security.csrf_token_for(cookie)):
            raise Forbidden(f"Missing or invalid {CSRF_HEADER} header.", code="csrf_failed")
    set_session_cookies(response, cookie, settings)
    return auth.Principal(user=session.user, via="session", session_token=cookie)


CurrentPrincipal = Annotated[auth.Principal, Depends(get_principal)]


async def get_human(principal: CurrentPrincipal) -> User:
    return auth.require_human(principal)


async def get_instance_admin(principal: CurrentPrincipal) -> User:
    return auth.require_instance_admin(principal)


HumanUser = Annotated[User, Depends(get_human)]
InstanceAdmin = Annotated[User, Depends(get_instance_admin)]
