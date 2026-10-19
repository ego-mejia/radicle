"""Sessions, API tokens and the identity behind every request."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core import security
from radicle.core.errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationFailed
from radicle.db.models import ApiToken, Session, User, UserKind, utcnow
from radicle.services.validation import normalize_token_name

SESSION_REFRESH_AFTER = timedelta(hours=1)
TOKEN_TOUCH_AFTER = timedelta(minutes=1)


@dataclass(frozen=True)
class Principal:
    user: User
    via: Literal["session", "token"]
    session_token: str | None = None


@dataclass(frozen=True)
class IssuedSession:
    token: str
    session: Session


@dataclass(frozen=True)
class IssuedToken:
    token: str
    record: ApiToken


def require_human(principal: Principal) -> User:
    if principal.user.kind is not UserKind.human:
        raise Forbidden("Agents cannot do this; it is only available to human users.")
    return principal.user


def require_instance_admin(principal: Principal) -> User:
    if not principal.user.is_instance_admin:
        raise Forbidden("Only instance admins can do this.")
    return principal.user


async def authenticate_password(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email.strip()))
    # Hash anyway when the user is missing so timing does not reveal which emails exist.
    password_hash = user.password_hash if user and user.password_hash else None
    valid = security.verify_password(password_hash or _DUMMY_HASH, password)
    if user is None or password_hash is None or not valid or not user.is_active:
        raise Unauthorized("Invalid email or password.", code="invalid_credentials")
    return user


_DUMMY_HASH = security.hash_password("radicle-dummy-password")


async def create_session(
    db: AsyncSession, user: User, *, days: int, ip: str | None, user_agent: str | None
) -> IssuedSession:
    token = security.generate_session_token()
    session = Session(
        user_id=user.id,
        token_hash=security.hash_token(token),
        expires_at=utcnow() + timedelta(days=days),
        ip=ip,
        user_agent=(user_agent or "")[:500] or None,
    )
    db.add(session)
    await db.flush()
    return IssuedSession(token=token, session=session)


async def resolve_session(db: AsyncSession, token: str, *, days: int) -> Session | None:
    """Return the live session for a cookie value, sliding its expiry forward."""
    session = await db.scalar(
        select(Session).where(Session.token_hash == security.hash_token(token))
    )
    now = utcnow()
    if session is None or session.expires_at <= now or not session.user.is_active:
        return None
    new_expiry = now + timedelta(days=days)
    if new_expiry - session.expires_at >= SESSION_REFRESH_AFTER:
        session.expires_at = new_expiry
    return session


async def delete_session(db: AsyncSession, token: str) -> None:
    session = await db.scalar(
        select(Session).where(Session.token_hash == security.hash_token(token))
    )
    if session is not None:
        await db.delete(session)


async def resolve_api_token(db: AsyncSession, token: str) -> User:
    if not security.is_api_token_format(token):
        raise Unauthorized(
            "Malformed API token. Tokens look like 'rdc_' plus 40 characters.", code="invalid_token"
        )
    record = await db.scalar(
        select(ApiToken).where(ApiToken.token_hash == security.hash_token(token))
    )
    now = utcnow()
    if record is None:
        raise Unauthorized("Unknown API token.", code="invalid_token")
    if record.revoked_at is not None:
        raise Unauthorized(
            "This API token was revoked. Ask an admin for a new one.", code="token_revoked"
        )
    if record.expires_at is not None and record.expires_at <= now:
        raise Unauthorized("This API token expired. Create a new one.", code="token_expired")
    if not record.user.is_active:
        raise Unauthorized("The user that owns this token is deactivated.", code="user_inactive")
    if record.last_used_at is None or now - record.last_used_at >= TOKEN_TOUCH_AFTER:
        record.last_used_at = now
    return record.user


async def issue_token(
    db: AsyncSession, user: User, name: str, expires_at: datetime | None = None
) -> IssuedToken:
    if expires_at is not None and expires_at <= utcnow():
        raise ValidationFailed(
            "expires_at must be in the future.",
            errors=[{"field": "expires_at", "message": "in the past"}],
        )
    token = security.generate_api_token()
    record = ApiToken(
        user_id=user.id,
        name=normalize_token_name(name),
        prefix=security.token_display_prefix(token),
        token_hash=security.hash_token(token),
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    return IssuedToken(token=token, record=record)


async def list_tokens(db: AsyncSession, user: User) -> list[ApiToken]:
    result = await db.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
    )
    return list(result)


async def revoke_token(db: AsyncSession, user: User, token_id: uuid.UUID) -> ApiToken:
    record = await db.scalar(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user.id)
    )
    if record is None:
        raise NotFound(f"Token {token_id} not found for @{user.handle}.")
    if record.revoked_at is not None:
        raise Conflict("This token is already revoked.", code="already_revoked")
    record.revoked_at = utcnow()
    return record
