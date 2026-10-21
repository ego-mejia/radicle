"""In-app notifications and preferences (ADR 0038): what the bell lists, marking read,
and each user's choice per notification type and channel."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, literal, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import Channel, Notification, NotificationPreference, User, utcnow
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import events

MAX_LIMIT = 100


async def list_for(
    db: AsyncSession,
    user: User,
    *,
    unread_only: bool = False,
    before: uuid.UUID | None = None,
    limit: int = 30,
) -> list[Notification]:
    """Newest first; `before` pages from a notification id."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    if before is not None:
        anchor = await db.get(Notification, before)
        if anchor is None or anchor.user_id != user.id:
            raise ValidationFailed(
                "Unknown cursor. Use next_cursor from the previous page.",
                errors=[{"field": "cursor", "message": "unknown"}],
            )
        query = query.where(
            tuple_(Notification.created_at, Notification.id)
            < tuple_(literal(anchor.created_at), literal(anchor.id))
        )
    rows = await db.scalars(
        query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    )
    return list(rows)


async def unread_count(db: AsyncSession, user: User) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return int(count or 0)


async def mark_read(db: AsyncSession, user: User, ids: list[uuid.UUID] | None) -> int:
    """Mark these (or, with None, all) of the user's notifications read; returns how many."""
    query = update(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    )
    if ids is not None:
        query = query.where(Notification.id.in_(ids))
    result = await db.execute(query.values(read_at=utcnow()))
    return int(getattr(result, "rowcount", 0) or 0)


@dataclass(frozen=True)
class Preference:
    app: str
    type: str
    label: str
    in_app: bool
    email: bool


async def preferences(db: AsyncSession, user: User) -> list[Preference]:
    """Every notification type the apps registered, with the user's choice or the default."""
    rows = await db.execute(
        select(
            NotificationPreference.app,
            NotificationPreference.type,
            NotificationPreference.channel,
            NotificationPreference.enabled,
        ).where(NotificationPreference.user_id == user.id)
    )
    chosen = {(a, t, c): e for a, t, c, e in rows.all()}
    out = []
    for kind in sorted(events.event_types(), key=lambda k: (k.app, k.label)):
        on = {c: chosen.get((kind.app, kind.type, c), c in kind.defaults) for c in Channel}
        out.append(
            Preference(kind.app, kind.type, kind.label, on[Channel.in_app], on[Channel.email])
        )
    return out


async def set_preference(
    db: AsyncSession, user: User, app: str, type: str, channel: Channel, enabled: bool
) -> None:
    known = {(k.app, k.type) for k in events.event_types()}
    if (app, type) not in known:
        valid = ", ".join(sorted(f"{a}.{t}" for a, t in known))
        raise ValidationFailed(
            f"Unknown notification type {app}.{type}. Valid ones: {valid}.",
            errors=[{"field": "type", "message": "unknown"}],
        )
    await db.execute(
        insert(NotificationPreference)
        .values(user_id=user.id, app=app, type=type, channel=channel, enabled=enabled)
        .on_conflict_do_update(
            index_elements=["user_id", "app", "type", "channel"], set_={"enabled": enabled}
        )
    )
