"""Folio's editable catalogs (Folio 1.3): document types, audiences and languages. Folio
admins add, rename, reorder and archive entries; publishing only accepts active ones."""

import re
from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioAudience, FolioDocType, FolioLanguage
from radicle.platform import authz
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import Conflict, NotFound, ValidationFailed

Catalog = Literal["doc-types", "audiences", "languages"]
Entry = FolioDocType | FolioAudience | FolioLanguage
MODELS: dict[Catalog, type[FolioDocType] | type[FolioAudience] | type[FolioLanguage]] = {
    "doc-types": FolioDocType,
    "audiences": FolioAudience,
    "languages": FolioLanguage,
}
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def entries(
    db: AsyncSession, catalog: Catalog, *, include_archived: bool = False
) -> list[Entry]:
    model = MODELS[catalog]
    query = select(model).order_by(model.position, model.key)
    if not include_archived:
        query = query.where(model.archived_at.is_(None))
    return list(await db.scalars(query))


async def active_keys(db: AsyncSession, catalog: Catalog) -> list[str]:
    return [e.key for e in await entries(db, catalog)]


async def _admin(db: AsyncSession, user: User) -> None:
    (await authz.authorize(db, user, "folio", "folio.admin")).raise_if_denied()


def _name(value: str) -> str:
    name = value.strip()
    if not 1 <= len(name) <= 80:
        raise _invalid("name", "Names are 1 to 80 characters.")
    return name


async def create(
    db: AsyncSession, user: User, catalog: Catalog, *, key: str, name: str, description: str = ""
) -> Entry:
    await _admin(db, user)
    key = key.strip().lower()
    if not KEY_RE.fullmatch(key):
        raise _invalid("key", f"Invalid key '{key}'. Use lowercase letters, digits and dashes.")
    model = MODELS[catalog]
    if await db.get(model, key) is not None:
        raise Conflict(f"'{key}' is already in {catalog}.", code="catalog_key_taken")
    last = await entries(db, catalog, include_archived=True)
    entry = model(
        key=key,
        name=_name(name),
        description=description.strip(),
        position=max((e.position for e in last), default=-1) + 1,
    )
    db.add(entry)
    await db.flush()
    return entry


@dataclass(frozen=True)
class EntryChanges:
    name: str | None = None
    description: str | None = None
    position: int | None = None
    archived: bool | None = None


async def update(
    db: AsyncSession, user: User, catalog: Catalog, key: str, ch: EntryChanges
) -> Entry:
    await _admin(db, user)
    entry = cast(Entry | None, await db.get(MODELS[catalog], key))
    if entry is None:
        raise NotFound(f"'{key}' is not in {catalog}.", code="catalog_entry_not_found")
    if ch.name is not None:
        entry.name = _name(ch.name)
    if ch.description is not None:
        entry.description = ch.description.strip()
    if ch.position is not None:
        entry.position = ch.position
    if ch.archived is not None:
        entry.archived_at = utcnow() if ch.archived else None
    await db.flush()
    return entry
