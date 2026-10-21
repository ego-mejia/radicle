"""The docs chat (Folio 4.5) with seeded docs and a simulated provider: it cites the right
section, says when the docs don't cover something, streams, and takes feedback."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.chat import ChatFeedback, FolioChatMessage
from radicle.folio.db.models import FolioSpace, FolioSpaceGrant, GranteeType
from radicle.folio.services import chat, retrieval, search
from radicle.platform.db.models import AiCall, User
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_chat_helpers import docs, model, user

__all__ = ["docs", "model"]  # fixtures


async def run(db: AsyncSession, who: User, question: str, **kw: object) -> list[chat.Event]:
    session = await chat.create_session(db, who)
    return [e async for e in await chat.ask(db, who, session, question, **kw)]  # type: ignore[arg-type]


async def test_acceptance_cites_the_right_section(
    db: AsyncSession, team: Team, docs: dict, model: list[dict]
) -> None:
    member = await user(db, team.member.handle)
    events = await run(db, member, "¿Cómo conecto un agente?")
    assert [e.data["text"] for e in events if e.name == "delta"] == ["Ve a ", "Admin, Agentes [1]."]
    done = events[-1]
    assert done.name == "done"
    cited = done.data["message"]["citations"]
    assert cited[0]["node_id"] == docs["guide"] and cited[0]["anchor"] == "conecta-un-agente"
    assert cited[0]["url"].endswith("#conecta-un-agente") and cited[0]["version"] == 1
    system = model[0]["system"]
    passages = system.split("Passages:\n\n")[1]
    assert passages.startswith("[1] Conecta un agente a Radicle > Conecta un agente\n")
    assert "Use only the numbered passages" in system
    saved = await db.get(FolioChatMessage, done.data["message"]["id"])
    assert saved is not None and saved.input_tokens == 300 and saved.output_tokens == 9
    calls = list(await db.scalars(select(AiCall)))
    assert [(c.app, c.feature, c.ok) for c in calls] == [("folio", "chat", True)]


async def test_says_when_the_docs_dont_cover_it(
    db: AsyncSession, team: Team, docs: dict, model: list[dict]
) -> None:
    member = await user(db, team.member.handle)
    events = await run(db, member, "¿Cuál es la receta del pozole?")
    assert model == []  # nothing retrieved: no model asked
    text = events[-1].data["message"]["content"]
    assert "No encontré esto en los docs" in text and events[-1].data["message"]["citations"] == []
    english = await run(db, member, "Whats the best pizza topping?")
    assert "couldn't find this in the docs" in english[-1].data["message"]["content"]


async def test_errors_feedback_and_unanswered(
    db: AsyncSession, team: Team, docs: dict, model: list[dict]
) -> None:
    member = await user(db, team.member.handle)
    admin = await user(db, team.instance.handle)
    session = await chat.create_session(db, member)
    with pytest.raises(ValidationFailed):
        await chat.ask(db, member, session, "   ")
    with pytest.raises(NotFound):
        await chat.get_session(db, admin, session.id)
    answered = await run(db, member, "¿Cómo conecto un agente?")
    missing = await run(db, member, "¿Cuál es la receta del pozole?")
    good_id = answered[-1].data["message"]["id"]
    rated = await chat.give_feedback(db, member, good_id, ChatFeedback.down, "Falta el token")
    assert rated.feedback == ChatFeedback.down and rated.feedback_note == "Falta el token"
    with pytest.raises(NotFound):
        await chat.give_feedback(db, admin, good_id, ChatFeedback.up, None)
    with pytest.raises(Forbidden):
        await chat.unanswered(db, member)
    rows = await chat.unanswered(db, admin)
    assert [r.question for r in rows] == [
        "¿Cuál es la receta del pozole?",
        "¿Cómo conecto un agente?",
    ]
    assert missing[-1].data["message"]["citations"] == []


async def test_without_a_chat_model_the_chat_refuses(db: AsyncSession, team: Team) -> None:
    member = await user(db, team.member.handle)
    session = await chat.create_session(db, member)
    with pytest.raises(ValidationFailed, match="AI provider"):
        await chat.ask(db, member, session, "¿Cómo conecto un agente?")


async def test_who_to_ask_is_the_closest_owner(db: AsyncSession, team: Team, docs: dict) -> None:
    found = await retrieval.retrieve(
        db, await user(db, team.member.handle), "subir a producción con docker"
    )
    assert found[0].node_id.hex == docs["deploy"].replace("-", "")
    assert await chat.contact(db, found, None) == f"@{team.member.handle}"
    assert await chat.contact(db, [], None) == "a Folio admin"
    space = await db.scalar(select(FolioSpace).where(FolioSpace.key == "docs"))
    assert space is not None
    db.add(
        FolioSpaceGrant(
            space_id=space.id,
            grantee_type=GranteeType.user,
            grantee_id=(await user(db, team.member.handle)).id,
            permissions=["view", "admin"],
        )
    )
    await db.flush()
    admins = f"@{team.instance.handle} or @{team.member.handle}"
    assert await chat.contact(db, [], "docs") == admins


async def test_outdated_docs_are_cited_with_a_warning(
    db: AsyncSession, team: Team, docs: dict
) -> None:
    member = await user(db, team.member.handle)
    found = await retrieval.retrieve(db, member, "docker", filters=search.Filters(doc_type="guide"))
    found[0].status = "outdated"
    assert "(OUTDATED)" in chat._passages_text(found)
    cited = chat.citations("Así [1] y [9] y [1].", found)
    assert len(cited) == 1 and cited[0]["outdated"] is True
