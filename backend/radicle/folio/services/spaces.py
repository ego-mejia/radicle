"""Folio spaces (Folio 1.1): team spaces anyone in Folio can read, and one personal space
per person that only they see. Space permissions arrive with 1.4."""

import re
from dataclasses import dataclass

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioSpace, SpaceKind
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed

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


def _visible(user: User) -> ColumnElement[bool]:
    """Team spaces and the user's own personal space, not deleted."""
    return (FolioSpace.deleted_at.is_(None)) & or_(
        FolioSpace.kind == SpaceKind.team, FolioSpace.owner_id == user.id
    )


async def list_spaces(db: AsyncSession, user: User) -> list[FolioSpace]:
    """Team spaces by name, then your personal space."""
    rows = await db.scalars(
        select(FolioSpace).where(_visible(user)).order_by(FolioSpace.kind, FolioSpace.name)
    )
    return list(rows)


async def get_space(db: AsyncSession, user: User, key: str) -> FolioSpace:
    space = await db.scalar(
        select(FolioSpace).where(FolioSpace.key == key.strip().lower(), _visible(user))
    )
    if space is None:
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
    return space


@dataclass(frozen=True)
class SpaceChanges:
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    clear_icon: bool = False


async def can_manage(db: AsyncSession, user: User, space: FolioSpace) -> bool:
    """Until space permissions (1.4): its creator, its owner, or a Folio admin."""
    if space.owner_id == user.id or space.created_by == user.id:
        return True
    return (await authz.authorize(db, user, "folio", "folio.admin")).allowed


async def _require_manage(db: AsyncSession, user: User, space: FolioSpace) -> None:
    if not await can_manage(db, user, space):
        raise Forbidden(f"Only the admins of {space.name} can change it.", code="space_admin_only")


async def update_space(
    db: AsyncSession, user: User, space: FolioSpace, ch: SpaceChanges
) -> FolioSpace:
    await _require_manage(db, user, space)
    if ch.name is not None:
        space.name = _name(ch.name)
    if ch.description is not None:
        space.description = _description(ch.description)
    if ch.clear_icon:
        space.icon = None
    elif ch.icon is not None:
        space.icon = ch.icon.strip() or None
    space.updated_at = utcnow()
    await db.flush()
    return space


async def delete_space(db: AsyncSession, user: User, space: FolioSpace) -> None:
    """Soft delete: the space and everything in it disappear, history stays."""
    await _require_manage(db, user, space)
    if space.kind == SpaceKind.personal:
        raise _invalid("key", "Personal spaces cannot be deleted.")
    space.deleted_at = utcnow()
    await db.flush()
