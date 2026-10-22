"""The Specs and Architecture decisions sections of a space (RAD-57): the published build
specs and decision logs the reader can see, with what the tables filter on. A spec's status
comes from the tickets it created (Folio 4.3) with the reader's Docket access; a decision's
number is its order of first publication in the space (ADR 0045)."""

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.docket_links import FolioTicketLink, TicketLinkKind
from radicle.folio.db.models import FolioNode, FolioSpace, FolioVersion, NodeStatus
from radicle.folio.services import access
from radicle.folio.services.metadata import DECISION_STATUSES
from radicle.platform.db.models import User
from radicle.platform.errors import ValidationFailed

SPEC_TYPE = "build-spec"
DECISION_TYPE = "decision-log"
MAX_ROWS = 500
SPEC_STATUSES = ("planned", "live", "done", "outdated")
DECISION_FILTERS = ("current", "all", *DECISION_STATUSES)


@dataclass
class Page:
    node: FolioNode
    metadata: dict[str, Any]
    owner_name: str | None


@dataclass
class Spec(Page):
    project: str | None = None
    features: list[str] = field(default_factory=list)
    status: str = "planned"
    done: int = 0
    in_progress: int = 0
    total: int = 0


@dataclass
class Specs:
    items: list[Spec]
    total: int
    projects: list[tuple[str, int]]
    features: list[tuple[str, int]]
    owners: list[tuple[str, str, int]]


@dataclass
class Decision(Page):
    number: int = 0
    topic: str | None = None
    project: str | None = None
    status: str = "accepted"
    replaces: int | None = None
    replaced_by: int | None = None


@dataclass
class Decisions:
    items: list[Decision]
    total: int
    hidden_replaced: int
    topics: list[tuple[str, int]]
    projects: list[tuple[str, int]]


def _invalid(field_name: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field_name, "message": "invalid"}])


async def _published(db: AsyncSession, user: User, space: FolioSpace, doc_type: str) -> list[Page]:
    """Published, non-archived pages of a doc type that the user can see, oldest first."""
    rows = await db.execute(
        select(FolioNode, FolioVersion.metadata_)
        .join(FolioVersion, FolioVersion.id == FolioNode.published_version_id)
        .where(
            FolioNode.space_id == space.id,
            FolioNode.archived_at.is_(None),
            FolioVersion.metadata_["doc_type"].astext == doc_type,
            await access.node_filter(db, user),
        )
        .order_by(FolioNode.published_at, FolioNode.id)
        .limit(MAX_ROWS)
    )
    pages = [(node, dict(meta or {})) for node, meta in rows.all()]
    handles = {str(m.get("owner") or "") for _, m in pages} - {""}
    names: dict[str, str] = {}
    if handles:
        found = await db.execute(
            select(User.handle, User.display_name).where(User.handle.in_(handles))
        )
        names = {h: n for h, n in found.all()}
    return [Page(node, m, names.get(str(m.get("owner") or ""))) for node, m in pages]


def _matches(page: Page, q: str) -> bool:
    text = f"{page.node.title} {page.metadata.get('description', '')}".lower()
    return all(word in text for word in q.lower().split())


def _newest(page: Page) -> datetime:
    return page.node.published_at or page.node.updated_at


async def list_specs(
    db: AsyncSession,
    user: User,
    space: FolioSpace,
    *,
    project: str | None = None,
    features: list[str] | None = None,
    status: str | None = None,
    owner: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Specs:
    if status and status not in SPEC_STATUSES:
        raise _invalid(
            "status", f"Unknown status {status}. Use one of: {', '.join(SPEC_STATUSES)}."
        )
    pages = await _published(db, user, space, SPEC_TYPE)
    specs = [
        Spec(
            p.node,
            p.metadata,
            p.owner_name,
            project=p.metadata.get("docket_project") or None,
            features=list(p.metadata.get("docket_areas") or []),
        )
        for p in pages
    ]
    await _progress(db, user, specs)
    project = project.strip().upper() if project else None
    wanted = set(features or [])
    projects = Counter(s.project for s in specs if s.project)
    in_project = [s for s in specs if project is None or s.project == project]
    feature_counts = Counter(f for s in in_project for f in s.features) if project else Counter()
    owners = Counter((str(s.metadata.get("owner") or ""), s.owner_name or "") for s in specs)
    rows = [
        s
        for s in in_project
        if (not wanted or wanted & set(s.features))
        and (not status or s.status == status)
        and (not owner or s.metadata.get("owner") == owner.strip().lstrip("@").lower())
        and (not q or _matches(s, q))
    ]
    rows.sort(key=_newest, reverse=True)
    return Specs(
        items=rows[offset : offset + limit],
        total=len(rows),
        projects=sorted(projects.items(), key=lambda kv: (-kv[1], kv[0])),
        features=sorted(feature_counts.items(), key=lambda kv: (-kv[1], kv[0])),
        owners=sorted(
            ((h, n, c) for (h, n), c in owners.items() if h), key=lambda o: (-o[2], o[1])
        ),
    )


async def _progress(db: AsyncSession, user: User, specs: list[Spec]) -> None:
    """Each spec's tickets from its deliverables, as far as the reader can see them in Docket."""
    by_node = {s.node.id: s for s in specs}
    if not by_node:
        return
    links = await db.execute(
        select(FolioTicketLink.node_id, FolioTicketLink.ticket_id).where(
            FolioTicketLink.node_id.in_(by_node),
            FolioTicketLink.kind == TicketLinkKind.build_spec_item,
        )
    )
    pairs: list[tuple[uuid.UUID, uuid.UUID]] = [(n, t) for n, t in links.all()]
    tickets = await docket.get_tickets_by_id(db, list({t for _, t in pairs}), user)
    for node_id, ticket_id in pairs:
        ticket = tickets.get(ticket_id)
        if ticket is None:
            continue
        spec = by_node[node_id]
        spec.total += 1
        spec.done += ticket.status_category == "done"
        spec.in_progress += ticket.status_category == "in_progress"
    for spec in specs:
        if spec.node.status == NodeStatus.outdated:
            spec.status = "outdated"
        elif spec.total and spec.done == spec.total:
            spec.status = "done"
        elif spec.done or spec.in_progress:
            spec.status = "live"
        else:
            spec.status = "planned"


async def list_decisions(
    db: AsyncSession,
    user: User,
    space: FolioSpace,
    *,
    topic: str | None = None,
    project: str | None = None,
    status: str = "current",
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Decisions:
    if status not in DECISION_FILTERS:
        raise _invalid(
            "status", f"Unknown status {status}. Use one of: {', '.join(DECISION_FILTERS)}."
        )
    pages = await _published(db, user, space, DECISION_TYPE)
    decisions = [
        Decision(
            p.node,
            p.metadata,
            p.owner_name,
            number=i,
            topic=p.metadata.get("decision_topic") or None,
            project=p.metadata.get("docket_project") or None,
            status=p.metadata.get("decision_status") or "accepted",
        )
        for i, p in enumerate(pages, start=1)
    ]
    by_id = {str(d.node.id): d for d in decisions}
    for d in decisions:
        old = by_id.get(str(d.metadata.get("decision_replaces") or ""))
        if old is not None and old is not d:
            d.replaces = old.number
            old.replaced_by = d.number
            old.status = "replaced"
    topics = Counter(d.topic for d in decisions if d.topic)
    projects = Counter(d.project for d in decisions if d.project)
    replaced = [d for d in decisions if d.status == "replaced"]
    rows = [
        d
        for d in decisions
        if (not topic or d.topic == topic)
        and (not project or d.project == project.strip().upper())
        and (
            status == "all"
            or (d.status != "replaced" if status == "current" else d.status == status)
        )
        and (not q or _matches(d, q))
    ]
    rows.sort(key=lambda d: d.number, reverse=True)
    return Decisions(
        items=rows[offset : offset + limit],
        total=len(rows),
        hidden_replaced=len(replaced) if status == "current" else 0,
        topics=sorted(topics.items(), key=lambda kv: (-kv[1], kv[0])),
        projects=sorted(projects.items(), key=lambda kv: (-kv[1], kv[0])),
    )
