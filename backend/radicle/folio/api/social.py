"""Following, favorites, reactions and your reading history over REST (Folio 2.4, 2.7)."""

import uuid
from typing import Literal

from fastapi import APIRouter, Response

from radicle.folio.api.spaces import NodeRef, SpaceOut, _ref, _space
from radicle.folio.db.collab import TargetType
from radicle.folio.services import social
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, Page

router = APIRouter(tags=["folio"])

Followable = Literal["node", "space"]


class FavoritesOut(Output):
    nodes: list[NodeRef]
    spaces: list[SpaceOut]


class WatchOut(Output):
    watching: bool


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/watch/{target_type}/{target_id}", response_model=WatchOut)
async def get_watch(
    target_type: Followable, target_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> WatchOut:
    await _reader(db, principal)
    kind = TargetType(target_type)
    await social.target(db, principal.user, kind, target_id)
    return WatchOut(watching=await social.is_watching(db, principal.user, kind, target_id))


@router.put("/watch/{target_type}/{target_id}", status_code=204)
async def watch(
    target_type: Followable, target_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    """Follow a page or a space: you hear about its comments and publications."""
    await _reader(db, principal)
    await social.watch(db, principal.user, TargetType(target_type), target_id)
    return Response(status_code=204)


@router.delete("/watch/{target_type}/{target_id}", status_code=204)
async def unwatch(
    target_type: Followable, target_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    await _reader(db, principal)
    await social.unwatch(db, principal.user, TargetType(target_type), target_id)
    return Response(status_code=204)


@router.put("/favorites/{target_type}/{target_id}", status_code=204)
async def favorite(
    target_type: Followable, target_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    await _reader(db, principal)
    await social.favorite(db, principal.user, TargetType(target_type), target_id)
    return Response(status_code=204)


@router.delete("/favorites/{target_type}/{target_id}", status_code=204)
async def unfavorite(
    target_type: Followable, target_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Response:
    await _reader(db, principal)
    await social.unfavorite(db, principal.user, TargetType(target_type), target_id)
    return Response(status_code=204)


@router.get("/me/recents", response_model=Page[NodeRef])
async def recents(principal: CurrentPrincipal, db: Db) -> Page[NodeRef]:
    """What you read last, newest first."""
    await _reader(db, principal)
    return Page(items=[_ref(n) for n in await social.recents(db, principal.user)])


@router.get("/me/favorites", response_model=FavoritesOut)
async def favorites(principal: CurrentPrincipal, db: Db) -> FavoritesOut:
    """Your starred pages and spaces."""
    await _reader(db, principal)
    nodes, spaces = await social.favorites(db, principal.user)
    return FavoritesOut(
        nodes=[_ref(n) for n in nodes],
        spaces=[await _space(db, principal.user, s) for s in spaces],
    )
