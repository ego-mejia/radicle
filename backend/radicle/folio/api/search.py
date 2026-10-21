"""Searching Folio over REST (Folio 1.6): /api/v1/folio/search."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.services import analytics
from radicle.folio.services import search as search_service
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output

router = APIRouter(tags=["folio"])


class HitOut(Output):
    node_id: uuid.UUID
    title: str
    description: str
    section: list[str] = Field(description="Heading path of the best matching section")
    anchor: str | None
    url: str = Field(description="Link to the page, at the section")
    snippet: str = Field(description="Matching words between ** for text matches")
    space: str
    doc_type: str | None
    score: float
    matched_by: list[str] = Field(description="text, semantic or both")
    status: Literal["draft", "published", "in_review", "verified", "outdated"]


class SearchOut(Output):
    mode: Literal["hybrid", "text", "semantic"]
    items: list[HitOut]
    search_id: uuid.UUID = Field(
        description="Send it to /analytics/searches/{search_id}/click with the result opened"
    )


@router.get("/search", response_model=SearchOut)
async def search(
    principal: CurrentPrincipal,
    db: Db,
    q: str = Query(min_length=1, max_length=500, description="Words or a question"),
    mode: Literal["hybrid", "text", "semantic"] = "hybrid",
    space: str | None = None,
    kind: Literal["page", "blog_post"] | None = None,
    doc_type: str | None = None,
    label: str | None = None,
    author: str | None = None,
    owner: str | None = None,
    audience: str | None = None,
    language: str | None = None,
    published_from: date | None = Query(default=None, alias="from"),
    published_to: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchOut:
    """Pages you can see, one result per page at its best section. Hybrid fuses text and
    semantic search; without an AI provider it is text only."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    filters = search_service.Filters(
        space=space,
        kind=kind,
        doc_type=doc_type,
        label=label,
        author=author,
        owner=owner,
        audience=audience,
        language=language,
        published_from=published_from,
        published_to=published_to,
    )
    hits = await search_service.search(
        db, principal.user, q, mode=mode, filters=filters, limit=limit
    )
    logged = await analytics.log_search(db, principal.user, q, mode, len(hits))
    return SearchOut(
        mode=mode,
        search_id=logged.id,
        items=[
            HitOut(
                node_id=h.node_id,
                title=h.title,
                description=h.description,
                section=h.heading_path,
                anchor=h.anchor,
                url=h.url,
                snippet=h.snippet,
                space=h.space,
                doc_type=h.doc_type,
                score=h.score,
                matched_by=h.matched_by,
                status=h.status,
            )
            for h in hits
        ],
    )
