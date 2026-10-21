"""Querying docs with RQL over REST (Folio 1.6): GET /api/v1/folio/nodes?q=<rql>."""

import uuid
from typing import Any

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.db.models import NodeKind
from radicle.folio.services import doc_query
from radicle.platform import authz
from radicle.platform.api.deps import AppSettings, CurrentPrincipal, Db
from radicle.platform.api.schemas import Output, Page, UtcDatetime

router = APIRouter(tags=["folio"])


class DocOut(Output):
    id: uuid.UUID
    kind: NodeKind
    title: str
    slug: str
    icon: str | None
    space: str
    parent_id: uuid.UUID | None
    published_at: UtcDatetime | None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    version: int | None = Field(description="Published version; null until first published")
    metadata: dict[str, Any] | None = Field(description="Of the published version")


@router.get("/nodes", response_model=Page[DocOut])
async def query_nodes(
    principal: CurrentPrincipal,
    db: Db,
    settings: AppSettings,
    q: str = Query(
        default="",
        max_length=2000,
        description="RQL, e.g. space = ai-tools AND doc_type = how-to ORDER BY published DESC",
    ),
    limit: int = Query(default=doc_query.DEFAULT_LIMIT, ge=1, le=doc_query.MAX_LIMIT),
    cursor: str | None = None,
) -> Page[DocOut]:
    """Pages, folders and posts you can see that match the query; errors say where."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    result = await doc_query.query(
        db, principal.user, q, limit=limit, cursor=cursor, timezone=settings.timezone
    )
    return Page(
        items=[
            DocOut(
                id=d.node.id,
                kind=d.node.kind,
                title=d.node.title,
                slug=d.node.slug,
                icon=d.node.icon,
                space=d.space,
                parent_id=d.node.parent_id,
                published_at=d.node.published_at,
                created_at=d.node.created_at,
                updated_at=d.node.updated_at,
                version=d.version.number if d.version else None,
                metadata=d.version.metadata_ if d.version else None,
            )
            for d in result.items
        ],
        next_cursor=result.next_cursor,
    )
