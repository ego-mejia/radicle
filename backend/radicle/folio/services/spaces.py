"""Folio spaces (Folio 1.1): team spaces, and one personal space per person that only they
see. Who sees and changes each one comes from its grants (`access`, Folio 1.4)."""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioSpace, SpaceKind
from radicle.folio.services import access
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, NotFound, ValidationFailed

KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
NAME_MAX = 120
DESCRIPTION_MAX = 1000


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def _key(value: str) -> str:
    key = value.strip().lower()
    if not KEY_RE.fullmatch(key):
        raise _invalid(
            "key",
            f"Invalid space key '{value}'. Use 2 to 40 lowercase letters, digits and dashes, "
            "starting with a letter or digit, e.g. ai-tools.",
        )
    return key


def _name(value: str) -> str:
    name = value.strip()
    if not 1 <= len(name) <= NAME_MAX:
        raise _invalid("name", f"Space names are 1 to {NAME_MAX} characters.")
    return name


def _description(value: str) -> str:
    text = value.strip()
    if len(text) > DESCRIPTION_MAX:
        raise _invalid("description", f"Descriptions are up to {DESCRIPTION_MAX} characters.")
    return text


def _not_found(key: str) -> NotFound:
    return NotFound(
        f"Space '{key}' not found. GET /api/v1/folio/spaces lists the ones you can see.",
        code="space_not_found",
    )


async def list_spaces(db: AsyncSession, user: User) -> list[FolioSpace]:
    """Team spaces by name, then your personal space."""
    ids = await access.visible_space_ids(db, user)
    rows = await db.scalars(
        select(FolioSpace).where(FolioSpace.id.in_(ids)).order_by(FolioSpace.kind, FolioSpace.name)
    )
    return list(rows)


async def get_space(db: AsyncSession, user: User, key: str) -> FolioSpace:
    space = await db.scalar(select(FolioSpace).where(FolioSpace.key == key.strip().lower()))
    if space is None or space.id not in await access.visible_space_ids(db, user):
        raise _not_found(key)
    return space


async def create_space(
    db: AsyncSession,
    user: User,
    *,
    key: str,
    name: str,
    description: str = "",
    icon: str | None = None,
) -> FolioSpace:
    """A team space. Folio creators and admins may create them."""
    (await authz.authorize(db, user, "folio", "folio.create")).raise_if_denied()
    key = _key(key)
    if await db.scalar(select(FolioSpace.id).where(FolioSpace.key == key)):
        raise Conflict(f"The space key '{key}' is taken. Choose another.", code="space_key_taken")
    space = FolioSpace(
        key=key,
        name=_name(name),
        description=_description(description),
        kind=SpaceKind.team,
        icon=(icon or "").strip() or None,
        created_by=user.id,
    )
    db.add(space)
    await db.flush()
    db.add_all(access.default_grants(space, user))
    await db.flush()
    return space


async def personal_space(db: AsyncSession, user: User) -> FolioSpace:
    """Your personal space, created the first time you ask for it."""
    space = await db.scalar(
        select(FolioSpace).where(
            FolioSpace.kind == SpaceKind.personal,
            FolioSpace.owner_id == user.id,
            FolioSpace.deleted_at.is_(None),
        )
    )
    if space is not None:
        return space
    base = re.sub(r"[^a-z0-9]+", "-", f"me-{user.handle.lower()}").strip("-")[:36]
    key, n = base, 1
    while await db.scalar(select(FolioSpace.id).where(FolioSpace.key == key)):
        n += 1
        key = f"{base}-{n}"
    space = FolioSpace(
        key=key,
        name=user.display_name,
        kind=SpaceKind.personal,
        owner_id=user.id,
        created_by=user.id,
    )
    db.add(space)
    await db.flush()
    db.add_all(access.default_grants(space, user))
    await db.flush()
    return space


@dataclass(frozen=True)
class SpaceChanges:
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    clear_icon: bool = False
    verify_days: int | None = None
    ai_enabled: bool | None = None
    show_readers: bool | None = None


MAX_VERIFY_DAYS = 730


async def can_manage(db: AsyncSession, user: User, space: FolioSpace) -> bool:
    return "admin" in await access.space_permissions(db, user, space)


async def update_space(
    db: AsyncSession, user: User, space: FolioSpace, ch: SpaceChanges
) -> FolioSpace:
    await access.require_admin(db, user, space)
    if ch.name is not None:
        space.name = _name(ch.name)
    if ch.description is not None:
        space.description = _description(ch.description)
    if ch.clear_icon:
        space.icon = None
    elif ch.icon is not None:
        space.icon = ch.icon.strip() or None
    if ch.verify_days is not None:
        if not 1 <= ch.verify_days <= MAX_VERIFY_DAYS:
            raise _invalid(
                "verify_days",
                f"A verification lasts 1 to {MAX_VERIFY_DAYS} days; {ch.verify_days} is out "
                "of range.",
            )
        space.verify_days = ch.verify_days
    if ch.ai_enabled is not None:
        space.ai_enabled = ch.ai_enabled
    if ch.show_readers is not None:
        space.show_readers = ch.show_readers
    space.updated_at = utcnow()
    await db.flush()
    return space


async def delete_space(db: AsyncSession, user: User, space: FolioSpace) -> None:
    """Soft delete: the space and everything in it disappear, history stays."""
    await access.require_admin(db, user, space)
    if space.kind == SpaceKind.personal:
        raise _invalid("key", "Personal spaces cannot be deleted.")
    space.deleted_at = utcnow()
    await db.flush()
