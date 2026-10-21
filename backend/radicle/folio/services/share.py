"""Sharing a page with a message (Folio 2.4). The people and groups chosen get a
notification; with `grant_view`, those a page restriction keeps out are added to it."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioPageRestriction, GranteeType, RestrictionMode
from radicle.folio.services import access, nodes, rag
from radicle.folio.services.notices import APP, node_link
from radicle.platform.db.models import Group, GroupMember, OutboxEvent, User
from radicle.platform.errors import Forbidden, ValidationFailed
from radicle.platform.services import events, groups, users

MAX_MESSAGE = 2000
MAX_TARGETS = 50


@dataclass(frozen=True)
class Shared:
    notified: list[str]  # handles who will hear about it
    cannot_see: list[str]  # handles the page stays hidden from
    granted: list[str]  # handles and group names added to the view restriction


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def _members(db: AsyncSession, group: Group) -> list[User]:
    rows = await db.scalars(
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group.id)
    )
    return list(rows)


async def _own_view_restriction(db: AsyncSession, node: FolioNode) -> set[uuid.UUID] | None:
    """The grantees of the node's own view restriction, or None when it has none."""
    rows = await db.scalars(
        select(FolioPageRestriction.grantee_id).where(
            FolioPageRestriction.node_id == node.id,
            FolioPageRestriction.mode == RestrictionMode.view,
        )
    )
    found = set(rows)
    return found or None


async def _grant(
    db: AsyncSession, sharer: User, node: FolioNode, people: list[User], chosen: list[Group]
) -> list[str]:
    """Let whoever can't see the page in, through its own view restriction."""
    blocked = [u for u in people if not await access.can_view(db, u, node.id)]
    if not blocked:
        return []
    own = await _own_view_restriction(db, node)
    if own is None or not await access.may_edit(db, sharer, node):
        names = ", ".join(f"@{u.handle}" for u in blocked)
        raise Forbidden(
            f"{names} can't see '{node.title}' and you can't let them in from here: its "
            "restriction comes from a page above it, or you can't edit this page. Ask "
            "someone who can edit the restricted page.",
            code="cannot_grant_view",
        )
    grantees: list[tuple[GranteeType, uuid.UUID, str]] = [
        (GranteeType.group, g.id, g.name) for g in chosen
    ]
    in_groups = {u.id for g in chosen for u in await _members(db, g)}
    grantees += [(GranteeType.user, u.id, u.handle) for u in blocked if u.id not in in_groups]
    added = []
    for kind, gid, name in grantees:
        if gid not in own:
            db.add(
                FolioPageRestriction(
                    node_id=node.id, mode=RestrictionMode.view, grantee_type=kind, grantee_id=gid
                )
            )
            added.append(name)
    await db.flush()
    nodes.record(db, node, sharer, "shared_view", added=added)
    await rag.schedule(db, await rag.subtree(db, node))
    return added


async def share(
    db: AsyncSession,
    sharer: User,
    node: FolioNode,
    *,
    handles: list[str],
    group_names: list[str],
    message: str,
    grant_view: bool = False,
) -> Shared:
    if not handles and not group_names:
        raise _invalid("users", "Choose at least one person or group to share with.")
    if len(handles) + len(group_names) > MAX_TARGETS:
        raise _invalid("users", f"Share with up to {MAX_TARGETS} people and groups at once.")
    message = message.strip()
    if len(message) > MAX_MESSAGE:
        raise _invalid("message", f"Keep the message under {MAX_MESSAGE} characters.")
    chosen = [await groups.get_group(db, name) for name in group_names]
    found = {}
    for handle in handles:
        user = await users.get_by_handle(db, handle)
        found[user.id] = user
    for group in chosen:
        found.update({u.id: u for u in await _members(db, group)})
    people = [u for u in found.values() if u.is_active and u.id != sharer.id]
    granted = await _grant(db, sharer, node, people, chosen) if grant_view else []
    can_see = [u for u in people if await access.can_view(db, u, node.id)]
    if can_see:
        payload = {
            "node_id": str(node.id),
            "user_ids": [str(u.id) for u in can_see],
            "message": message,
        }
        await events.emit(db, APP, "page_shared", actor=sharer, payload=payload)
    return Shared(
        notified=sorted(u.handle for u in can_see),
        cannot_see=sorted(u.handle for u in people if u not in can_see),
        granted=granted,
    )


@events.resolver(APP, "page_shared", label="Someone shares a page with you")
async def _shared(db: AsyncSession, event: OutboxEvent) -> list[events.Notice]:
    node = await db.get(FolioNode, uuid.UUID(event.payload["node_id"]))
    if node is None or node.deleted_at is not None:
        return []
    actor = await db.get(User, event.actor_id) if event.actor_id else None
    title = f"{actor.display_name if actor else 'Someone'} shared '{node.title}' with you"
    ids = [uuid.UUID(i) for i in event.payload["user_ids"]]
    people = await db.scalars(select(User).where(User.id.in_(ids)))
    message = str(event.payload.get("message", ""))
    return [
        events.Notice(u.id, "shared", title, message, node_link(node))
        for u in people
        if await access.can_view(db, u, node.id)
    ]
