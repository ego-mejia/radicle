"""First-run setup, humans and agents."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core import mcp_tools, security
from radicle.core.errors import Conflict, NotFound, ValidationFailed
from radicle.db.models import User, UserKind
from radicle.services import auth
from radicle.services.validation import check_password, normalize_display_name, normalize_handle

# Serialises concurrent POST /setup calls so only one admin is ever created.
_SETUP_LOCK_KEY = 0x5AD1C1E


@dataclass(frozen=True)
class UserChanges:
    display_name: str | None = None
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_instance_admin: bool | None = None
    # Agents only. `set_mcp_tools` says whether to change them; None then means all tools.
    set_mcp_tools: bool = False
    mcp_tools: list[str] | None = None


def check_mcp_tools(names: list[str] | None) -> list[str] | None:
    """The tools an agent may call, in catalog order; None (all tools) stays None."""
    if names is None:
        return None
    known = mcp_tools.known()
    unknown = sorted(set(names) - set(known))
    if unknown:
        raise ValidationFailed(
            f"Unknown MCP tool: {', '.join(unknown)}. GET /api/v1/mcp/tools lists the valid ones.",
            code="unknown_mcp_tool",
            errors=[{"field": "mcp_tools", "message": "unknown tool"}],
        )
    chosen = set(names)
    return [n for n in known if n in chosen]


async def needs_setup(db: AsyncSession) -> bool:
    count = await db.scalar(
        select(func.count()).select_from(User).where(User.kind != UserKind.system)
    )
    return count == 0


async def create_first_admin(
    db: AsyncSession, *, handle: str, display_name: str, email: str, password: str
) -> User:
    await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SETUP_LOCK_KEY})
    if not await needs_setup(db):
        raise Conflict(
            "Setup is already done. Sign in with an existing account.", code="setup_done"
        )
    return await create_human(
        db,
        handle=handle,
        display_name=display_name,
        email=email,
        password=password,
        is_instance_admin=True,
    )


async def create_human(
    db: AsyncSession,
    *,
    handle: str,
    display_name: str,
    email: str,
    password: str,
    is_instance_admin: bool = False,
) -> User:
    user = User(
        handle=normalize_handle(handle),
        display_name=normalize_display_name(display_name),
        email=email.strip(),
        kind=UserKind.human,
        password_hash=security.hash_password(check_password(password)),
        is_instance_admin=is_instance_admin,
    )
    return await _insert(db, user)


async def create_agent(
    db: AsyncSession,
    *,
    handle: str,
    display_name: str,
    token_name: str,
    mcp_tools: list[str] | None = None,
) -> tuple[User, auth.IssuedToken]:
    user = User(
        handle=normalize_handle(handle),
        display_name=normalize_display_name(display_name),
        kind=UserKind.agent,
        mcp_tools=check_mcp_tools(mcp_tools),
    )
    user = await _insert(db, user)
    issued = await auth.issue_token(db, user, token_name)
    return user, issued


async def _insert(db: AsyncSession, user: User) -> User:
    await _ensure_unique(db, handle=user.handle, email=user.email)
    db.add(user)
    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError as exc:
        raise Conflict("Handle or email is already taken.", code="duplicate_user") from exc
    return user


async def _ensure_unique(
    db: AsyncSession, *, handle: str | None, email: str | None, exclude: User | None = None
) -> None:
    if handle is not None:
        query = select(User.id).where(User.handle == handle)
        if exclude is not None:
            query = query.where(User.id != exclude.id)
        if await db.scalar(query):
            raise Conflict(
                f"Handle @{handle} is already taken.",
                code="duplicate_handle",
                errors=[{"field": "handle", "message": "already taken"}],
            )
    if email is not None:
        query = select(User.id).where(User.email == email)
        if exclude is not None:
            query = query.where(User.id != exclude.id)
        if await db.scalar(query):
            raise Conflict(
                f"Email {email} is already registered.",
                code="duplicate_email",
                errors=[{"field": "email", "message": "already registered"}],
            )


async def get_by_handle(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle.lstrip("@").lower()))
    if user is None:
        raise NotFound(f"User @{handle.lstrip('@')} not found.")
    return user


async def list_users(
    db: AsyncSession, *, limit: int, after: tuple[datetime, str] | None
) -> list[User]:
    query = (
        select(User)
        .where(User.kind != UserKind.system)
        .order_by(User.created_at, User.id)
        .limit(limit)
    )
    if after is not None:
        query = query.where(tuple_(User.created_at, User.id) > after)
    return list(await db.scalars(query))


async def update_user(db: AsyncSession, user: User, changes: UserChanges) -> User:
    if changes.display_name is not None:
        user.display_name = normalize_display_name(changes.display_name)
    if changes.email is not None or changes.password is not None:
        if user.kind is UserKind.agent:
            raise ValidationFailed(
                "Agents have no email or password; they use API tokens.", code="agent_credentials"
            )
    if changes.email is not None:
        email = changes.email.strip()
        await _ensure_unique(db, handle=None, email=email, exclude=user)
        user.email = email
    if changes.password is not None:
        user.password_hash = security.hash_password(check_password(changes.password))
    removing_admin = changes.is_instance_admin is False and user.is_instance_admin
    deactivating_admin = changes.is_active is False and user.is_instance_admin
    if (removing_admin or deactivating_admin) and await _active_admin_count(db) <= 1:
        raise Conflict(
            "This is the last active instance admin. Make someone else admin first.",
            code="last_admin",
        )
    if changes.is_instance_admin is not None:
        if changes.is_instance_admin and user.kind is UserKind.agent:
            raise ValidationFailed("Agents cannot be instance admins.", code="agent_admin")
        user.is_instance_admin = changes.is_instance_admin
    if changes.is_active is not None:
        user.is_active = changes.is_active
    if changes.set_mcp_tools:
        if user.kind is not UserKind.agent:
            raise ValidationFailed(
                "Only agents have MCP tool limits; people follow their project permissions.",
                code="not_an_agent",
                errors=[{"field": "mcp_tools", "message": "agents only"}],
            )
        user.mcp_tools = check_mcp_tools(changes.mcp_tools)
    await db.flush()
    return user


async def change_own_password(
    db: AsyncSession, user: User, *, current_password: str, new_password: str
) -> None:
    if user.password_hash is None or not security.verify_password(
        user.password_hash, current_password
    ):
        raise ValidationFailed(
            "Current password is incorrect.",
            code="wrong_password",
            errors=[{"field": "current_password", "message": "incorrect"}],
        )
    user.password_hash = security.hash_password(check_password(new_password))


async def _active_admin_count(db: AsyncSession) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_instance_admin.is_(True), User.is_active.is_(True))
    )
    return int(count or 0)
