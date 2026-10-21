"""People you can mention in Folio (Folio 2.3): who can read Folio, by handle or name."""

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, Page
from radicle.platform.db.models import User, UserKind

router = APIRouter(tags=["folio"])
LIMIT = 10


class FolioPersonOut(Output):
    handle: str
    name: str
    kind: str


@router.get("/people", response_model=Page[FolioPersonOut])
async def people(
    principal: CurrentPrincipal,
    db: Db,
    q: str = Query(default="", max_length=64, description="Start of a handle or a name"),
) -> Page[FolioPersonOut]:
    """For @mentions: active people and agents who can read Folio, best matches first."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    text = q.strip().lstrip("@")
    query = select(User).where(User.is_active.is_(True), User.kind != UserKind.system)
    if text:
        query = query.where(
            or_(User.handle.ilike(f"{text}%"), User.display_name.ilike(f"%{text}%"))
        )
    found = []
    for user in await db.scalars(query.order_by(User.handle).limit(LIMIT * 5)):
        if (await authz.authorize(db, user, "folio", "folio.read")).allowed:
            found.append(
                FolioPersonOut(handle=user.handle, name=user.display_name, kind=user.kind.value)
            )
        if len(found) == LIMIT:
            break
    return Page(items=found)
