"""The Specs section of a space over REST (RAD-57)."""

from typing import Literal

from fastapi import APIRouter, Query

from radicle.folio.api.spaces import NodeRef, _ref
from radicle.folio.services import sections, spaces
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, UtcDatetime

router = APIRouter(tags=["folio"])


class Count(Output):
    value: str
    count: int


class OwnerCount(Output):
    handle: str
    name: str
    count: int


class SpecRowOut(Output):
    node: NodeRef
    description: str
    project: str | None
    features: list[str]
    status: Literal["planned", "live", "done", "outdated"]
    tickets_done: int
    tickets_in_progress: int
    tickets_total: int
    owner: str | None
    owner_name: str | None
    updated_at: UtcDatetime


class SpecListOut(Output):
    items: list[SpecRowOut]
    total: int
    projects: list[Count]
    features: list[Count]
    owners: list[OwnerCount]


@router.get("/spaces/{key}/specs", response_model=SpecListOut)
async def list_specs(
    key: str,
    principal: CurrentPrincipal,
    db: Db,
    project: str | None = Query(default=None, description="Docket project key, e.g. RAD"),
    feature: list[str] = Query(default=[], description="Docket areas of that project"),
    status: Literal["planned", "live", "done", "outdated"] | None = None,
    owner: str | None = Query(default=None, description="Owner handle"),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SpecListOut:
    """The space's published build specs you can see, newest first, with their tickets'
    progress and the counts the filters show. `feature` only applies with `project`."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    space = await spaces.get_space(db, principal.user, key)
    found = await sections.list_specs(
        db,
        principal.user,
        space,
        project=project,
        features=feature,
        status=status,
        owner=owner,
        q=q,
        limit=limit,
        offset=offset,
    )
    return SpecListOut(
        items=[
            SpecRowOut(
                node=_ref(s.node),
                description=str(s.metadata.get("description") or ""),
                project=s.project,
                features=s.features,
                status=s.status,
                tickets_done=s.done,
                tickets_in_progress=s.in_progress,
                tickets_total=s.total,
                owner=s.metadata.get("owner"),
                owner_name=s.owner_name,
                updated_at=s.node.published_at or s.node.updated_at,
            )
            for s in found.items
        ],
        total=found.total,
        projects=[Count(value=v, count=c) for v, c in found.projects],
        features=[Count(value=v, count=c) for v, c in found.features],
        owners=[OwnerCount(handle=h, name=n or h, count=c) for h, n, c in found.owners],
    )
