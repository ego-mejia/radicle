"""A space at a glance (RAD-57): its sections, how many pages and folders it has, and who
takes part. Sections group published pages by doc type; the space admin may hide or
reorder them."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioNode,
    FolioSpace,
    FolioSpaceGrant,
    FolioVersion,
    GranteeType,
    NodeKind,
)
from radicle.folio.services import access
from radicle.platform.db.models import GroupMember, User, UserKind, utcnow
from radicle.platform.errors import ValidationFailed

# Each section lists the published pages whose doc type is one of these, in this order.
SECTION_DOC_TYPES: dict[str, tuple[str, ...]] = {
    "specs": ("build-spec",),
    "decisions": ("decision-log",),
    "guides": ("how-to", "guide"),
    "docs": ("reference",),
}
ROLE_ORDER = {"admin": 0, "editor": 1, "reader": 2}


@dataclass(frozen=True)
class Section:
    key: str
    doc_types: tuple[str, ...]
    visible: bool
    count: int = 0


@dataclass(frozen=True)
class Participant:
    handle: str
    name: str
    kind: str
    role: str


@dataclass(frozen=True)
class Overview:
    pages: int
    folders: int
    sections: list[Section]
    participants: list[Participant]
    everyone_role: str | None


def sections_of(space: FolioSpace) -> list[Section]:
    """The space's sections in order. Sections it doesn't mention come last, shown."""
    stored = space.sections or []
    seen: set[str] = set()
    out: list[Section] = []
    for item in stored:
        key = str(item.get("key", ""))
        if key in SECTION_DOC_TYPES and key not in seen:
            seen.add(key)
            out.append(Section(key, SECTION_DOC_TYPES[key], bool(item.get("visible", True))))
    out += [Section(k, t, True) for k, t in SECTION_DOC_TYPES.items() if k not in seen]
    return out


async def set_sections(
    db: AsyncSession, user: User, space: FolioSpace, items: Sequence[tuple[str, bool]]
) -> list[Section]:
    """Order and show or hide the sections. Only the space's admins may."""
    await access.require_admin(db, user, space)
    keys = [k for k, _ in items]
    unknown = [k for k in keys if k not in SECTION_DOC_TYPES]
    if unknown:
        valid = ", ".join(SECTION_DOC_TYPES)
        raise ValidationFailed(
            f"Unknown section {unknown[0]!r}. Sections are: {valid}.",
            errors=[{"field": "sections", "message": "unknown"}],
        )
    if len(set(keys)) != len(keys):
        raise ValidationFailed(
            "Each section may appear once.", errors=[{"field": "sections", "message": "duplicate"}]
        )
    space.sections = [{"key": k, "visible": v} for k, v in items]
    space.updated_at = utcnow()
    await db.flush()
    return sections_of(space)


def _role(permissions: list[str]) -> str:
    if "admin" in permissions:
        return "admin"
    return "editor" if "create" in permissions else "reader"


async def _participants(
    db: AsyncSession, space: FolioSpace
) -> tuple[list[Participant], str | None]:
    grants = list(
        await db.scalars(select(FolioSpaceGrant).where(FolioSpaceGrant.space_id == space.id))
    )
    roles: dict[uuid.UUID, str] = {}

    def keep(user_id: uuid.UUID, role: str) -> None:
        if user_id not in roles or ROLE_ORDER[role] < ROLE_ORDER[roles[user_id]]:
            roles[user_id] = role

    everyone: str | None = None
    for g in grants:
        role = _role(g.permissions)
        if g.grantee_type == GranteeType.everyone:
            everyone = role
        elif g.grantee_type == GranteeType.user and g.grantee_id is not None:
            keep(g.grantee_id, role)
        elif g.grantee_type == GranteeType.group and g.grantee_id is not None:
            members = await db.scalars(
                select(GroupMember.user_id).where(GroupMember.group_id == g.grantee_id)
            )
            for member in members:
                keep(member, role)
    if space.owner_id is not None:
        keep(space.owner_id, "admin")
    if not roles:
        return [], everyone
    users = await db.scalars(
        select(User).where(
            User.id.in_(roles), User.is_active.is_(True), User.kind != UserKind.system
        )
    )
    people = [Participant(u.handle, u.display_name, u.kind.value, roles[u.id]) for u in users]
    people.sort(key=lambda p: (ROLE_ORDER[p.role], p.name.lower()))
    return people, everyone


async def overview(db: AsyncSession, user: User, space: FolioSpace) -> Overview:
    """What the reader can see in the space: counts only include pages they may open."""
    visible = await access.node_filter(db, user)
    live = (
        FolioNode.space_id == space.id,
        FolioNode.archived_at.is_(None),
        FolioNode.deleted_at.is_(None),
        visible,
    )
    kinds = (
        await db.execute(select(FolioNode.kind, func.count()).where(*live).group_by(FolioNode.kind))
    ).all()
    folders = sum(int(n) for kind, n in kinds if kind == NodeKind.folder)
    pages = sum(int(n) for kind, n in kinds if kind != NodeKind.folder)
    doc_type = FolioVersion.metadata_["doc_type"].astext
    by_type: dict[str, int] = dict(
        (
            await db.execute(
                select(doc_type, func.count())
                .join(FolioNode, FolioNode.published_version_id == FolioVersion.id)
                .where(*live)
                .group_by(doc_type)
            )
        ).all()
    )
    sections = [
        Section(s.key, s.doc_types, s.visible, sum(int(by_type.get(t, 0)) for t in s.doc_types))
        for s in sections_of(space)
    ]
    people, everyone = await _participants(db, space)
    return Overview(
        pages=pages,
        folders=folders,
        sections=sections,
        participants=people,
        everyone_role=everyone,
    )
