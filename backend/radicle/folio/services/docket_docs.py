"""Docs of a Docket milestone or area (Folio 4.4). A published doc names them in its
optional metadata (docket_project, docket_milestones, docket_areas); Docket's milestone
and area views list those docs, filtered by what the reader may see on both sides."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import radicle.docket.public as docket
from radicle.folio.db.models import FolioNode, FolioSpace, FolioVersion
from radicle.folio.services import access
from radicle.platform.db.models import User
from radicle.platform.errors import NotFound, ValidationFailed

MAX_DOCS = 100


@dataclass(frozen=True)
class Doc:
    node: FolioNode
    space_key: str
    description: str
    doc_type: str | None


def parse_ref(ref: str, field: str) -> tuple[str, str]:
    """`PA:V1` → ("PA", "V1")."""
    project, sep, name = ref.partition(":")
    if not sep or not project.strip() or not name.strip():
        raise ValidationFailed(
            f"{field} is the project key and the name, like PA:V1.",
            errors=[{"field": field, "message": "invalid"}],
        )
    return project.strip().upper(), name.strip()


async def _docs(db: AsyncSession, user: User, project: str, field: str, name: str) -> list[Doc]:
    meta = FolioVersion.metadata_
    names = func.jsonb_array_elements_text(meta[field]).table_valued("value").alias("n")
    named = select(names.c.value).where(func.lower(names.c.value) == name.lower()).exists()
    rows = await db.execute(
        select(FolioNode, FolioSpace.key, FolioVersion.metadata_)
        .join(FolioVersion, FolioVersion.id == FolioNode.published_version_id)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .where(
            FolioNode.deleted_at.is_(None),
            FolioNode.archived_at.is_(None),
            meta["docket_project"].astext == project,
            func.jsonb_typeof(meta[field]) == "array",
            named,
            await access.node_filter(db, user),
        )
        .order_by(FolioNode.published_at.desc(), FolioNode.id)
        .limit(MAX_DOCS)
    )
    return [
        Doc(node, space, str(m.get("description") or ""), m.get("doc_type"))
        for node, space, m in rows
    ]


async def docs_for_milestone(db: AsyncSession, user: User, ref: str) -> list[Doc]:
    project, name = parse_ref(ref, "milestone")
    found = await docket.get_milestone(db, project, name, user)
    if found is None:
        raise NotFound(
            f"Milestone {name} not found in {project}, or you can't see it in Docket.",
            code="milestone_not_found",
        )
    return await _docs(db, user, found.project, "docket_milestones", found.name)


async def docs_for_area(db: AsyncSession, user: User, ref: str) -> list[Doc]:
    project, name = parse_ref(ref, "area")
    found = await docket.get_area(db, project, name, user)
    if found is None:
        raise NotFound(
            f"Area {name} not found in {project}, or you can't see it in Docket.",
            code="area_not_found",
        )
    return await _docs(db, user, project, "docket_areas", found)
