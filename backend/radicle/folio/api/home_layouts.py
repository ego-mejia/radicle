"""The home editor over REST (Folio 3.2): Folio admins edit a draft of the home's grid,
publish it, and bring back an earlier layout."""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import home_layouts
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(prefix="/admin/home", tags=["folio"])


class HomeBlock(Input):
    id: str
    type: str = Field(description=", ".join(home_layouts.TYPES))
    x: int
    y: int
    w: int
    h: int
    config: dict[str, Any] = Field(default_factory=dict)


class HomeLayoutIn(Input):
    columns: int = 12
    blocks: list[HomeBlock]


class HomeLayoutBody(Output):
    columns: int
    blocks: list[dict[str, Any]]


class HomeDraftOut(Output):
    layout: HomeLayoutBody
    saved: bool = Field(description="False while it is the published layout, unedited")
    updated_at: UtcDatetime | None


class HomeLayoutVersionOut(Output):
    id: uuid.UUID
    layout: HomeLayoutBody
    is_active: bool
    published_at: UtcDatetime | None
    published_by: str | None


def _draft(d: home_layouts.Draft) -> HomeDraftOut:
    return HomeDraftOut(layout=HomeLayoutBody(**d.layout), saved=d.saved, updated_at=d.updated_at)


async def _version(db: Db, row: Any) -> HomeLayoutVersionOut:
    who = await db.get(User, row.created_by) if row.created_by else None
    return HomeLayoutVersionOut(
        id=row.id,
        layout=HomeLayoutBody(**row.layout),
        is_active=row.is_active,
        published_at=row.published_at,
        published_by=who.handle if who else None,
    )


@router.get("/draft", response_model=HomeDraftOut)
async def get_draft(principal: CurrentPrincipal, db: Db) -> HomeDraftOut:
    """The layout being edited, or the published one when nobody has started."""
    return _draft(await home_layouts.get_draft(db, principal.user))


@router.put("/draft", response_model=HomeDraftOut)
async def put_draft(body: HomeLayoutIn, principal: CurrentPrincipal, db: Db) -> HomeDraftOut:
    """Save the draft; 422 lists every block that's wrong (an RQL error says where)."""
    raw = body.model_dump()
    return _draft(await home_layouts.save_draft(db, principal.user, raw))


@router.post("/publish", response_model=HomeLayoutVersionOut, status_code=201)
async def publish(principal: CurrentPrincipal, db: Db) -> HomeLayoutVersionOut:
    """Readers see the draft from now on; the previous layout stays in the history."""
    return await _version(db, await home_layouts.publish(db, principal.user))


@router.get("/history", response_model=Page[HomeLayoutVersionOut])
async def history(principal: CurrentPrincipal, db: Db) -> Page[HomeLayoutVersionOut]:
    rows = await home_layouts.history(db, principal.user)
    return Page(items=[await _version(db, r) for r in rows])


@router.post("/history/{layout_id}/restore", response_model=HomeLayoutVersionOut, status_code=201)
async def restore(
    layout_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> HomeLayoutVersionOut:
    """Publish an earlier layout again, as a new entry in the history."""
    return await _version(db, await home_layouts.restore(db, principal.user, layout_id))
