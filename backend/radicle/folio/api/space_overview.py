"""A space at a glance over REST (RAD-57): /api/v1/folio/spaces/{key}/overview and
/spaces/{key}/sections."""

from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import space_overview, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output

router = APIRouter(tags=["folio"])

SectionKey = Literal["specs", "decisions", "guides", "docs"]
Role = Literal["admin", "editor", "reader"]


class SpaceSectionOut(Output):
    key: SectionKey
    doc_types: list[str] = Field(description="Published pages of these doc types are listed")
    visible: bool
    count: int = Field(description="Published pages you can open in this section")


class SpaceParticipantOut(Output):
    handle: str
    name: str
    kind: str = Field(description="human or agent")
    role: Role


class SpaceOverviewOut(Output):
    pages: int = Field(description="Pages you can open, folders apart")
    folders: int
    sections: list[SpaceSectionOut] = Field(description="In order, hidden ones included")
    participants: list[SpaceParticipantOut] = Field(description="Admins first")
    everyone_role: Role | None = Field(description="What everyone may do here, if anything")


class SpaceSectionIn(Input):
    key: SectionKey
    visible: bool = True


class SpaceSectionsIn(Input):
    sections: list[SpaceSectionIn] = Field(
        description="In the order to show them; any you leave out come last, shown"
    )


def _sections(items: list[space_overview.Section]) -> list[SpaceSectionOut]:
    return [
        SpaceSectionOut(key=s.key, doc_types=list(s.doc_types), visible=s.visible, count=s.count)
        for s in items
    ]


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/spaces/{key}/overview", response_model=SpaceOverviewOut)
async def get_overview(key: str, principal: CurrentPrincipal, db: Db) -> SpaceOverviewOut:
    """Counts of what you can open, the sections with their counts, and who takes part."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    o = await space_overview.overview(db, principal.user, space)
    return SpaceOverviewOut(
        pages=o.pages,
        folders=o.folders,
        sections=_sections(o.sections),
        participants=[
            SpaceParticipantOut(handle=p.handle, name=p.name, kind=p.kind, role=p.role)
            for p in o.participants
        ],
        everyone_role=o.everyone_role,
    )


@router.put("/spaces/{key}/sections", response_model=list[SpaceSectionOut])
async def put_sections(
    key: str, body: SpaceSectionsIn, principal: CurrentPrincipal, db: Db
) -> list[SpaceSectionOut]:
    """Order the space's sections and show or hide each. Space admins only."""
    await _reader(db, principal)
    space = await spaces.get_space(db, principal.user, key)
    items = [(s.key, s.visible) for s in body.sections]
    return _sections(await space_overview.set_sections(db, principal.user, space, items))
