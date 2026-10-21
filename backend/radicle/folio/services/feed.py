"""The "Para ti" feed (Folio 2.4, 2.7): what the pages and spaces you follow published
lately, then the week's most read in the spaces you can see."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.collab import FolioWatch, TargetType
from radicle.folio.db.models import FolioNode
from radicle.folio.services import access, views
from radicle.folio.services.home import Card, _cards, _published
from radicle.platform.db.models import User

Reason = Literal["following", "popular"]
POPULAR = 5


@dataclass(frozen=True)
class FeedItem:
    card: Card
    reason: Reason


async def feed(db: AsyncSession, user: User, limit: int = 20) -> list[FeedItem]:
    base = _published(await access.node_filter(db, user))
    watched = select(FolioWatch.target_id).where(FolioWatch.user_id == user.id)
    following = base.where(
        or_(
            FolioNode.id.in_(watched.where(FolioWatch.target_type == TargetType.node)),
            FolioNode.space_id.in_(watched.where(FolioWatch.target_type == TargetType.space)),
        )
    )
    out = [FeedItem(c, "following") for c in await _cards(db, following, limit)]
    seen = [i.card.id for i in out]
    room = min(POPULAR, limit - len(out))
    if room > 0:
        read = views.most_read_since(7)
        popular = (
            base.join(read, read.c.node_id == FolioNode.id)
            .order_by(None)
            .order_by(read.c.views.desc(), FolioNode.published_at.desc(), FolioNode.id)
        )
        if seen:
            popular = popular.where(FolioNode.id.not_in(seen))
        out += [FeedItem(c, "popular") for c in await _cards(db, popular, room)]
    return out
