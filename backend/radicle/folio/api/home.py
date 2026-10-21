"""Folio's home over REST (Folio 1.8): GET /api/v1/folio/home."""

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import home as home_service
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, UtcDatetime

router = APIRouter(tags=["folio"])


class CardOut(Output):
    id: uuid.UUID
    kind: Literal["page", "blog_post"]
    title: str
    slug: str
    icon: str | None
    cover_asset_id: uuid.UUID | None
    space: str
    space_name: str
    description: str
    doc_type: str | None
    labels: list[str]
    author: str | None = Field(description="Handle of who published it")
    author_name: str | None
    published_at: UtcDatetime | None
    reading_minutes: int
    status: Literal["draft", "published", "in_review", "verified", "outdated"]


class SpaceCountOut(Output):
    key: str
    name: str
    kind: Literal["team", "personal"]
    icon: str | None
    docs: int = Field(description="Published pages and posts you can see")


class HomeOut(Output):
    can_write: bool = Field(description="Creators and admins see the Write button")
    featured: CardOut | None
    announcement: CardOut | None = Field(description="Latest post labelled anuncio")
    ai_tools: list[CardOut] = Field(description="Latest docs of the ai-tools space")
    latest_posts: list[CardOut]
    spaces: list[SpaceCountOut]
    most_read: list[CardOut] = Field(description="By reads in the last 7 days")


def _card(c: home_service.Card) -> CardOut:
    return CardOut.model_validate(c, from_attributes=True)


@router.get("/home", response_model=HomeOut)
async def get_home(principal: CurrentPrincipal, db: Db) -> HomeOut:
    """The default bento with every block already resolved for you."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    h = await home_service.home(db, principal.user)
    return HomeOut(
        can_write=h.can_write,
        featured=_card(h.featured) if h.featured else None,
        announcement=_card(h.announcement) if h.announcement else None,
        ai_tools=[_card(c) for c in h.ai_tools],
        latest_posts=[_card(c) for c in h.latest_posts],
        spaces=[SpaceCountOut.model_validate(s, from_attributes=True) for s in h.spaces],
        most_read=[_card(c) for c in h.most_read],
    )
