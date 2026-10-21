"""Agents and approval (Folio 1.5), through the services."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import (
    FolioRole,
    FolioSpaceGrant,
    GranteeType,
    NodeKind,
    SubmissionStatus,
)
from radicle.folio.services import access, drafts, nodes, roles, spaces, submissions
from radicle.platform.db.models import User
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed
from radicle.platform.services import groups
from tests.conftest import Team
from tests.integration.folio_helpers import METADATA


@pytest.fixture(autouse=True)
def fresh_group_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups, "_cache", {})


async def user(db: AsyncSession, handle: str) -> User:
    found = await db.scalar(select(User).where(User.handle == handle))
    assert found is not None
    return found


@pytest.fixture
async def world(db: AsyncSession, team: Team) -> dict:
    admin, agent, luis = (
        await user(db, team.instance.handle),
        await user(db, team.agent.handle),
        await user(db, "luis"),
    )
    space = await spaces.create_space(db, admin, key="docs", name="Docs")
    for who in (agent, luis):
        await roles.set_grant(db, admin, GranteeType.user, who.handle, FolioRole.creator)
        db.add(
            FolioSpaceGrant(
                space_id=space.id,
                grantee_type=GranteeType.user,
                grantee_id=who.id,
                permissions=["create"],
            )
        )
    await db.flush()
    page = await nodes.create_node(db, agent, space, kind=NodeKind.page, title="Cambios")
    await drafts.save_draft(db, agent, page, content_md="# Semana\n\nTodo bien.", metadata=METADATA)
    return {"admin": admin, "agent": agent, "luis": luis, "space": space, "page": page}


async def test_agent_submission_waits_unseen_then_is_approved(
    db: AsyncSession, world: dict
) -> None:
    agent, admin, luis, page = world["agent"], world["admin"], world["luis"], world["page"]
    first = await submissions.submit(db, agent, page, change_note="Semana 42")
    second = await submissions.submit(db, agent, page, change_note="Semana 42, corregida")
    assert first.status == SubmissionStatus.superseded and second.status == SubmissionStatus.pending

    # An agent's new page is seen by the agent and admins only, even by space writers.
    assert not await access.can_view(db, luis, page.id)
    assert await access.can_view(db, agent, page.id)
    assert await access.can_view(db, admin, page.id)
    assert [
        s.id for s in await submissions.list_submissions(db, admin, SubmissionStatus.pending)
    ] == [second.id]
    assert len(await submissions.list_submissions(db, agent)) == 2
    assert await submissions.list_submissions(db, luis) == []

    version = await submissions.approve(db, admin, second, comment="Bien")
    assert (version.number, version.author_id, version.approved_by) == (1, agent.id, admin.id)
    assert version.change_note == "Semana 42, corregida"
    assert second.status == SubmissionStatus.approved and second.version_id == version.id
    assert await access.can_view(db, luis, page.id)


async def test_rejection_comes_back_to_the_agent(db: AsyncSession, world: dict) -> None:
    agent, admin = world["agent"], world["admin"]
    submission = await submissions.submit(db, agent, world["page"])
    with pytest.raises(ValidationFailed, match="agent reads"):
        await submissions.reject(db, admin, submission, comment="  ")
    await submissions.reject(db, admin, submission, comment="Falta el diagrama.")
    mine = await submissions.get_submission(db, agent, submission.id)
    assert mine.status == SubmissionStatus.rejected and mine.review_comment == "Falta el diagrama."
    with pytest.raises(Conflict, match="already rejected"):
        await submissions.approve(db, admin, submission)


async def test_only_reviewers_decide(db: AsyncSession, world: dict) -> None:
    submission = await submissions.submit(db, world["agent"], world["page"])
    with pytest.raises(Forbidden, match="space's admins"):
        await submissions.approve(db, world["luis"], submission)
    with pytest.raises(NotFound):
        await submissions.get_submission(db, world["luis"], submission.id)


async def test_submissions_need_a_draft_and_complete_metadata(
    db: AsyncSession, world: dict
) -> None:
    agent = world["agent"]
    bare = await nodes.create_node(db, agent, world["space"], kind=NodeKind.page, title="Vacía")
    with pytest.raises(ValidationFailed, match="no draft"):
        await submissions.submit(db, agent, bare)
    await drafts.save_draft(db, agent, bare, content_md="x", metadata={"doc_type": "how-to"})
    with pytest.raises(ValidationFailed, match="metadata"):
        await submissions.submit(db, agent, bare)
