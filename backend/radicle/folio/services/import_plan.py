"""The dry run of an import (Folio 5.3): every page with whether it will be created or
updated, who each source author becomes, its labels, files and problems. It creates
nothing; the plan is saved on the import for the admin to review before running it."""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.imports import FolioExternalRef, FolioImport, ImportSource, ImportStatus
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services.imports import read_bundle, require_import
from radicle.platform.db.models import User, UserKind
from radicle.platform.errors import Conflict, NotFound, ValidationFailed

OPTION_KEYS = {"authors", "default_metadata", "parent_id"}


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def _uuid(field: str, value: object) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise _invalid(field, f"{value} is not an id.") from None


def check_options(options: dict[str, Any]) -> dict[str, Any]:
    unknown = set(options) - OPTION_KEYS
    if unknown:
        raise _invalid("options", f"Unknown options: {', '.join(sorted(unknown))}.")
    authors = options.get("authors") or {}
    if not isinstance(authors, dict) or not all(
        isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in authors.items()
    ):
        raise _invalid("options.authors", "authors maps each source author to a user id or null.")
    metadata = options.get("default_metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise _invalid("options.default_metadata", "default_metadata is an object of metadata.")
    return {k: v for k, v in options.items() if v is not None}


@dataclass
class Person:
    id: uuid.UUID
    handle: str
    display_name: str


async def match_author(db: AsyncSession, name: str) -> Person | None:
    """A person by email, else by exact display name (ignoring case)."""
    query = select(User).where(User.is_active, User.kind == UserKind.human)
    if "@" in name:
        user = await db.scalar(query.where(User.email == name.strip()))
    else:
        found = list(
            await db.scalars(
                query.where(func.lower(User.display_name) == name.strip().lower()).limit(2)
            )
        )
        user = found[0] if len(found) == 1 else None
    return Person(user.id, user.handle, user.display_name) if user else None


async def _person(db: AsyncSession, pick: str) -> User | None:
    """A user id, or a handle (with or without @), as the import wizard picks people."""
    handle = pick.strip().lstrip("@")
    if re.fullmatch(r"[0-9a-fA-F-]{36}", handle):
        return await db.get(User, _uuid("options.authors", handle))
    return await db.scalar(select(User).where(User.handle == handle))


async def resolve_authors(
    db: AsyncSession, names: set[str], chosen: dict[str, str | None]
) -> dict[str, Person | None]:
    """Who each source author becomes: the admin's choice (a user id or handle), else the
    automatic match."""
    picked: dict[str, Person | None] = {}
    for name, pick in chosen.items():
        user = await _person(db, pick) if pick else None
        if pick and (user is None or not user.is_active or user.kind != UserKind.human):
            raise _invalid("options.authors", f"The person chosen for {name} doesn't exist.")
        picked[name] = Person(user.id, user.handle, user.display_name) if user else None
    return {
        name: picked[name] if name in picked else await match_author(db, name)
        for name in sorted(names)
    }


async def existing_nodes(
    db: AsyncSession, source: ImportSource, ids: list[str], space_id: uuid.UUID
) -> dict[str, Any]:
    """External id -> the live node it was imported as before into this space."""
    rows = await db.execute(
        select(FolioExternalRef.external_id, FolioNode)
        .join(FolioNode, FolioNode.id == FolioExternalRef.node_id)
        .where(
            FolioExternalRef.source == source,
            FolioExternalRef.external_id.in_(ids),
            FolioExternalRef.space_id == space_id,
            FolioNode.deleted_at.is_(None),
        )
    )
    return {external_id: node for external_id, node in rows.all()}


async def dry_run(
    db: AsyncSession, user: User, item: FolioImport, options: dict[str, Any]
) -> dict[str, Any]:
    """The plan, saved on the import: every page with what will happen to it."""
    space = await db.get(FolioSpace, item.target_space_id)
    if space is None:
        raise NotFound("The import's space no longer exists.")
    await require_import(db, user, space)
    if item.status in (ImportStatus.running, ImportStatus.done):
        raise Conflict(f"This import is {item.status.value}; upload the export again to redo it.")
    options = check_options(options)
    if options.get("parent_id"):
        parent = await db.get(FolioNode, _uuid("options.parent_id", options["parent_id"]))
        if parent is None or parent.space_id != space.id or parent.deleted_at is not None:
            raise _invalid("options.parent_id", f"Pick a page or folder of {space.name}.")
    found = await read_bundle(item)
    authors = await resolve_authors(
        db, {p.author for p in found.pages if p.author}, options.get("authors") or {}
    )
    before = await existing_nodes(db, item.source, [p.external_id for p in found.pages], space.id)
    pages = [
        {
            "external_id": p.external_id,
            "title": p.title,
            "kind": p.kind,
            "parent_id": p.parent_id,
            "action": "update" if p.external_id in before else "create",
            "author": p.author,
            "labels": p.labels,
            "attachments": len(found.refs(p)),
            "rows": len(p.rows),
            "errors": p.errors,
        }
        for p in found.pages
    ]
    report = {
        "pages": pages,
        "authors": [
            {
                "source": name,
                "user": {"id": str(u.id), "handle": u.handle, "name": u.display_name}
                if u
                else None,
            }
            for name, u in authors.items()
        ],
        "errors": found.errors,
        "totals": {
            "pages": sum(p["kind"] == "page" for p in pages),
            "folders": sum(p["kind"] == "folder" for p in pages),
            "databases": sum(p["kind"] == "database" for p in pages),
            "attachments": len(found.attachments),
            "updates": sum(p["action"] == "update" for p in pages),
            "with_errors": sum(bool(p["errors"]) for p in pages),
        },
    }
    item.options, item.report, item.status = options, report, ImportStatus.checked
    await db.flush()
    return report
