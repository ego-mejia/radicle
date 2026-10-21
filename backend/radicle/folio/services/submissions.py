"""Agents and approval (Folio 1.5): what an agent publishes becomes a pending submission;
a Folio or space admin approves it (it's published with the agent as author and the admin
as approver) or rejects it with a comment the agent reads over MCP."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioDraft,
    FolioNode,
    FolioSpace,
    FolioSubmission,
    FolioVersion,
    NodeKind,
    SubmissionStatus,
)
from radicle.folio.services import access, nodes, notices, publishing, schema, visuals
from radicle.folio.services.metadata import validate_metadata
from radicle.platform.db.models import User, UserKind, utcnow
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed


def _invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


async def submit(
    db: AsyncSession, agent: User, node: FolioNode, *, change_note: str | None = None
) -> FolioSubmission:
    """The agent's draft as a pending submission; an earlier pending one is superseded."""
    await access.require_edit(db, agent, node)
    if node.kind == NodeKind.database:
        raise _invalid("node", "Databases aren't published: add rows to them directly.")
    if node.kind == NodeKind.live_doc:
        raise _invalid(
            "node",
            "Live docs are never published: everyone who can see them reads them as they are "
            "written, and their history is in the snapshots.",
        )
    from radicle.folio.services import collab  # collab needs publishing, which needs us

    await collab.flush(node)  # send what is on screen right now
    draft = await db.get(FolioDraft, node.id, populate_existing=True)
    if draft is None:
        raise _invalid("draft", "There is no draft to send. Write the page first.")
    metadata = await validate_metadata(db, node, draft.metadata_)
    visuals.require_publishable(draft.content_json)
    await db.execute(
        update(FolioSubmission)
        .where(
            FolioSubmission.node_id == node.id,
            FolioSubmission.submitted_by == agent.id,
            FolioSubmission.status == SubmissionStatus.pending,
        )
        .values(status=SubmissionStatus.superseded, decided_at=utcnow())
    )
    submission = FolioSubmission(
        node_id=node.id,
        title=metadata["title"],
        content_json=schema.validate(draft.content_json),
        metadata_=metadata,
        change_note=(change_note or "").strip() or None,
        submitted_by=agent.id,
        status=SubmissionStatus.pending,
    )
    db.add(submission)
    await db.flush()
    nodes.record(db, node, agent, "submitted", submission=str(submission.id))
    await notices.submission_pending(db, agent, node, submission.id)
    return submission


async def _space_of(db: AsyncSession, submission: FolioSubmission) -> FolioSpace:
    node = await db.get(FolioNode, submission.node_id)
    space = await db.get(FolioSpace, node.space_id) if node else None
    if space is None:  # pragma: no cover - submissions cascade with their node
        raise NotFound(f"Submission {submission.id} not found.", code="submission_not_found")
    return space


async def can_review(db: AsyncSession, user: User, submission: FolioSubmission) -> bool:
    space = await _space_of(db, submission)
    return "admin" in await access.space_permissions(db, user, space)


async def get_submission(db: AsyncSession, user: User, submission_id: uuid.UUID) -> FolioSubmission:
    """Its agent or a reviewer may see it; for anyone else it doesn't exist."""
    submission = await db.get(FolioSubmission, submission_id)
    if submission is None or (
        submission.submitted_by != user.id and not await can_review(db, user, submission)
    ):
        raise NotFound(
            f"Submission {submission_id} not found. GET /api/v1/folio/submissions lists yours.",
            code="submission_not_found",
        )
    return submission


async def list_submissions(
    db: AsyncSession, user: User, status: SubmissionStatus | None = None
) -> list[FolioSubmission]:
    """Agents: their own. People: the ones in spaces they administer. Newest first."""
    query = select(FolioSubmission).order_by(FolioSubmission.created_at.desc())
    if status is not None:
        query = query.where(FolioSubmission.status == status)
    if user.kind != UserKind.human:
        return list(await db.scalars(query.where(FolioSubmission.submitted_by == user.id)))
    out = []
    for submission in await db.scalars(query.limit(500)):
        if submission.submitted_by == user.id or await can_review(db, user, submission):
            out.append(submission)
    return out


async def _decide(db: AsyncSession, user: User, submission: FolioSubmission) -> FolioNode:
    if not await can_review(db, user, submission):
        raise Forbidden(
            "Only Folio admins and the space's admins approve or reject submissions.",
            code="reviewers_only",
        )
    if submission.status != SubmissionStatus.pending:
        raise Conflict(
            f"This submission is already {submission.status.value}.", code="submission_decided"
        )
    node = await db.get(FolioNode, submission.node_id)
    if node is None:  # pragma: no cover - submissions cascade with their node
        raise NotFound(f"Submission {submission.id} not found.", code="submission_not_found")
    return node


async def approve(
    db: AsyncSession, user: User, submission: FolioSubmission, *, comment: str | None = None
) -> FolioVersion:
    """Publish it: the agent is the author and `user` the approver."""
    node = await _decide(db, user, submission)
    agent = await db.get(User, submission.submitted_by)
    if agent is None:  # pragma: no cover - users are never deleted
        raise NotFound("The agent is gone.", code="agent_not_found")
    metadata = await validate_metadata(db, node, submission.metadata_)
    version = await publishing.create_version(
        db,
        node,
        author=agent,
        content_json=submission.content_json,
        metadata=metadata,
        change_note=submission.change_note,
        approved_by=user,
    )
    submission.status = SubmissionStatus.approved
    submission.reviewed_by = user.id
    submission.review_comment = (comment or "").strip() or None
    submission.version_id = version.id
    submission.decided_at = utcnow()
    nodes.record(db, node, user, "approved", version=version.number)
    await db.flush()
    return version


async def reject(
    db: AsyncSession, user: User, submission: FolioSubmission, *, comment: str
) -> FolioSubmission:
    """Send it back with a comment the agent can read and act on."""
    node = await _decide(db, user, submission)
    text = comment.strip()
    if not text:
        raise _invalid("comment", "Say what to fix: the agent reads this comment.")
    submission.status = SubmissionStatus.rejected
    submission.reviewed_by = user.id
    submission.review_comment = text
    submission.decided_at = utcnow()
    nodes.record(db, node, user, "rejected", submission=str(submission.id))
    await db.flush()
    return submission
