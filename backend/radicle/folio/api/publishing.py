"""Publishing and version history over REST (Folio 1.3)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.db.models import FolioSubmission, FolioVersion
from radicle.folio.services import nodes, publishing, submissions, versions
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, Page, UtcDatetime
from radicle.platform.db.models import User, UserKind

router = APIRouter(tags=["folio"])


class VersionOut(Output):
    number: int
    title: str
    change_note: str | None
    author: str
    approved_by: str | None = Field(description="The admin who approved an agent's version")
    restored_from: int | None = Field(description="The version it restored, if any")
    created_at: UtcDatetime
    metadata: dict[str, Any]


class PublishIn(Input):
    change_note: str | None = Field(default=None, description="What changed, for the history")
    confirm: bool = Field(
        default=False, description="Publish even if someone published after this draft started"
    )


async def version_out(db: Db, v: FolioVersion) -> VersionOut:
    author = await db.get(User, v.author_id)
    approver = await db.get(User, v.approved_by) if v.approved_by else None
    restored = await db.get(FolioVersion, v.restored_from) if v.restored_from else None
    return VersionOut(
        number=v.number,
        title=v.title,
        change_note=v.change_note,
        author=author.handle if author else "",
        approved_by=approver.handle if approver else None,
        restored_from=restored.number if restored else None,
        created_at=v.created_at,
        metadata=v.metadata_,
    )


class SubmissionOut(Output):
    id: uuid.UUID
    node_id: uuid.UUID
    title: str
    status: Literal["pending", "approved", "rejected", "superseded"]
    change_note: str | None
    submitted_by: str
    reviewed_by: str | None
    review_comment: str | None = Field(description="Why it was rejected, for the agent")
    version: int | None = Field(description="The version it became, once approved")
    created_at: UtcDatetime
    decided_at: UtcDatetime | None
    metadata: dict[str, Any]


async def submission_out(db: Db, s: FolioSubmission) -> SubmissionOut:
    agent = await db.get(User, s.submitted_by)
    reviewer = await db.get(User, s.reviewed_by) if s.reviewed_by else None
    version = await db.get(FolioVersion, s.version_id) if s.version_id else None
    return SubmissionOut(
        id=s.id,
        node_id=s.node_id,
        title=s.title,
        status=s.status.value,
        change_note=s.change_note,
        submitted_by=agent.handle if agent else "",
        reviewed_by=reviewer.handle if reviewer else None,
        review_comment=s.review_comment,
        version=version.number if version else None,
        created_at=s.created_at,
        decided_at=s.decided_at,
        metadata=s.metadata_,
    )


@router.post(
    "/nodes/{node_id}/publish",
    response_model=VersionOut | SubmissionOut,
    status_code=201,
    responses={202: {"model": SubmissionOut, "description": "An agent's submission"}},
)
async def publish(
    node_id: uuid.UUID, body: PublishIn, principal: CurrentPrincipal, db: Db, response: Response
) -> VersionOut | SubmissionOut:
    """Publish the draft as the next version (201). Agents send it for approval instead
    (202, a submission). 422 lists every missing metadata field; 409 when someone published
    after this draft started (send `confirm` to go ahead)."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    if principal.user.kind != UserKind.human:
        submission = await submissions.submit(
            db, principal.user, node, change_note=body.change_note
        )
        response.status_code = 202
        return await submission_out(db, submission)
    version = await publishing.publish(
        db, principal.user, node, change_note=body.change_note, confirm=body.confirm
    )
    return await version_out(db, version)


class VersionContentOut(VersionOut):
    content_json: dict[str, Any]
    content_md: str


class BlockChangeOut(Output):
    op: Literal["equal", "added", "removed"]
    block: dict[str, Any]


class FieldChangeOut(Output):
    field: str
    before: Any
    after: Any


class DiffOut(Output):
    from_version: int
    to_version: int
    title: FieldChangeOut | None
    blocks: list[BlockChangeOut]
    metadata: list[FieldChangeOut]


class RestoreIn(Input):
    change_note: str | None = None


@router.get("/nodes/{node_id}/versions", response_model=Page[VersionOut])
async def list_versions(
    node_id: uuid.UUID, principal: CurrentPrincipal, db: Db
) -> Page[VersionOut]:
    """The page's history, newest first, with author, approver and note."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    return Page(items=[await version_out(db, v) for v in await versions.list_versions(db, node)])


@router.get("/nodes/{node_id}/versions/{number}", response_model=VersionContentOut)
async def get_version(
    node_id: uuid.UUID, number: int, principal: CurrentPrincipal, db: Db
) -> VersionContentOut:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    v = await versions.get_version(db, node, number)
    base = await version_out(db, v)
    return VersionContentOut(
        **base.model_dump(), content_json=v.content_json, content_md=v.content_md
    )


@router.get("/nodes/{node_id}/diff", response_model=DiffOut)
async def diff(
    node_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: Db,
    from_: Annotated[int, Query(alias="from", ge=1)],
    to: Annotated[int, Query(ge=1)],
) -> DiffOut:
    """Blocks added and removed, and metadata fields that changed, from one version to another."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    old, new = await versions.get_version(db, node, from_), await versions.get_version(db, node, to)
    d = versions.diff_versions(old, new)

    def field(c: versions.FieldChange) -> FieldChangeOut:
        return FieldChangeOut(field=c.field, before=c.before, after=c.after)

    return DiffOut(
        from_version=from_,
        to_version=to,
        title=field(d.title) if d.title else None,
        blocks=[BlockChangeOut(op=b.op, block=b.block) for b in d.blocks],
        metadata=[field(c) for c in d.metadata],
    )


@router.post(
    "/nodes/{node_id}/versions/{number}/restore", response_model=VersionOut, status_code=201
)
async def restore(
    node_id: uuid.UUID, number: int, body: RestoreIn, principal: CurrentPrincipal, db: Db
) -> VersionOut:
    """Publish an old version again as a new one; nothing is deleted."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    node = await nodes.get_node(db, principal.user, node_id)
    version = await versions.restore(db, principal.user, node, number, change_note=body.change_note)
    return await version_out(db, version)
