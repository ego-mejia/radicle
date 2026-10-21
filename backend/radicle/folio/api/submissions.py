"""The approval queue over REST (Folio 1.5): agents' submissions and their decisions."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from radicle.folio.api.publishing import (
    BlockChangeOut,
    FieldChangeOut,
    SubmissionOut,
    VersionOut,
    submission_out,
    version_out,
)
from radicle.folio.db.models import FolioNode, FolioVersion, SubmissionStatus
from radicle.folio.services import convert, publishing, schema, submissions, versions
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Page
from radicle.platform.db.models import AuditApp
from radicle.platform.services import audit

router = APIRouter(tags=["folio"])


class SubmissionDetailOut(SubmissionOut):
    content_json: dict[str, Any]
    content_md: str
    current_version: int | None = Field(description="The published version it would replace")
    blocks: list[BlockChangeOut] = Field(description="Against the published version")
    changes: list[FieldChangeOut] = Field(description="Title and metadata against it")


class DecisionIn(Input):
    comment: str | None = Field(default=None, description="Required to reject: what to fix")


@router.get("/submissions", response_model=Page[SubmissionOut])
async def list_submissions(
    principal: CurrentPrincipal,
    db: Db,
    status: Literal["pending", "approved", "rejected", "superseded"] | None = Query(default=None),
) -> Page[SubmissionOut]:
    """The approval queue for admins; their own submissions for agents."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    rows = await submissions.list_submissions(
        db, principal.user, SubmissionStatus(status) if status else None
    )
    return Page(items=[await submission_out(db, s) for s in rows])


@router.get("/submissions/{submission_id}", response_model=SubmissionDetailOut)
async def get_submission(
    submission_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> SubmissionDetailOut:
    """What it would publish, and how it differs from the published version."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    s = await submissions.get_submission(db, principal.user, submission_id)
    node = await db.get(FolioNode, s.node_id)
    current = await publishing.current_version(db, node) if node else None
    base = current or FolioVersion(title="", content_json=schema.empty(), metadata_={}, number=0)
    proposed = FolioVersion(title=s.title, content_json=s.content_json, metadata_=s.metadata_)
    d = versions.diff_versions(base, proposed)
    changes = ([d.title] if d.title else []) + d.metadata
    out = await submission_out(db, s)

    return SubmissionDetailOut(
        **out.model_dump(),
        content_json=s.content_json,
        content_md=convert.to_markdown(s.content_json),
        current_version=current.number if current else None,
        blocks=[BlockChangeOut(op=b.op, block=b.block) for b in d.blocks],
        changes=[FieldChangeOut(field=c.field, before=c.before, after=c.after) for c in changes],
    )


@router.post("/submissions/{submission_id}/approve", response_model=VersionOut, status_code=201)
async def approve(
    submission_id: uuid.UUID, body: DecisionIn, principal: CurrentPrincipal, db: Db
) -> VersionOut:
    """Publish it with the agent as author and you as approver."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    s = await submissions.get_submission(db, principal.user, submission_id)
    version = await submissions.approve(db, principal.user, s, comment=body.comment)
    audit.record(
        db,
        principal.user,
        "folio.submission_approve",
        target_type="folio_submission",
        target_id=s.id,
        after={"version": version.number},
        app=AuditApp.folio,
    )
    return await version_out(db, version)


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut)
async def reject(
    submission_id: uuid.UUID, body: DecisionIn, principal: CurrentPrincipal, db: Db
) -> SubmissionOut:
    """Send it back with a comment the agent reads over MCP."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    s = await submissions.get_submission(db, principal.user, submission_id)
    await submissions.reject(db, principal.user, s, comment=body.comment or "")
    audit.record(
        db,
        principal.user,
        "folio.submission_reject",
        target_type="folio_submission",
        target_id=s.id,
        after={"comment": s.review_comment},
        app=AuditApp.folio,
    )
    return await submission_out(db, s)
