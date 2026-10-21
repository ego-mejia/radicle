"""Comments (Folio 2.3). Acceptance: an inline comment stays in place after the paragraph is
edited and turns orphaned when its text is deleted."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import comments
from radicle.platform.db.models import Notification, User
from radicle.platform.errors import Conflict, Forbidden, ValidationFailed
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish

MD = "# Agentes\n\nCrea el agente en Admin y conéctalo por MCP con su token.\n\nFin."


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def page(client: AsyncClient, db: AsyncSession, team: Team) -> FolioNode:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    await publish(client, team, r.json()["id"], md=MD)
    await _everyone_may(client, team, ["view", "comment"])
    node = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert node is not None
    return node


async def _everyone_may(client: AsyncClient, team: Team, permissions: list[str]) -> None:
    grants = [
        {"grantee_type": "everyone", "permissions": permissions},
        {"grantee_type": "user", "grantee": team.instance.handle, "permissions": ["admin"]},
    ]
    r = await client.put(
        f"{API}/spaces/docs/grants", headers=team.instance.headers, json={"grants": grants}
    )
    assert r.status_code == 200, r.text


async def _edit(client: AsyncClient, team: Team, page: FolioNode, md: str) -> None:
    r = await client.put(
        f"{API}/nodes/{page.id}/draft", headers=team.instance.headers, json={"content_md": md}
    )
    assert r.status_code == 200, r.text


async def test_acceptance_an_inline_comment_follows_its_text(
    client: AsyncClient, db: AsyncSession, team: Team, page: FolioNode
) -> None:
    luis = await _user(db, "luis")
    c = await comments.create(
        db, luis, page, body="¿Y el token dónde?", inline=True, quote="conéctalo por MCP"
    )
    assert c.anchor is not None and c.anchor["quote"] == "conéctalo por MCP"

    await _edit(client, team, page, "Intro nueva.\n\n" + MD)  # before
    await _edit(client, team, page, MD.replace("Fin.", "Fin, con nota."))  # after
    await db.refresh(c)
    assert not c.orphaned and c.anchor["quote"] == "conéctalo por MCP"

    await _edit(client, team, page, MD.replace("conéctalo por", "conéctalo desde Claude por"))
    await db.refresh(c)
    assert not c.orphaned and c.anchor["quote"] == "conéctalo desde Claude por MCP"

    await _edit(client, team, page, MD.replace("conéctalo por MCP ", ""))
    await db.refresh(c)
    assert c.orphaned  # its text is gone: shown in the panel with its quote
    await _edit(client, team, page, MD)
    await db.refresh(c)
    assert not c.orphaned  # and back when the text returns


async def test_threads_replies_resolve_and_reopen(
    db: AsyncSession, team: Team, page: FolioNode
) -> None:
    luis, ana = await _user(db, "luis"), await _user(db, "ana")
    root = await comments.create(db, luis, page, body="¿Esto sigue vigente?")
    await comments.create(db, ana, page, body="Sí, desde ayer.", thread_id=root.id)
    found = await comments.threads(db, luis, page)
    assert len(found) == 1 and [comments.body_md(r) for r in found[0].replies] == [
        "Sí, desde ayer."
    ]
    await comments.resolve(db, ana, root)
    assert await comments.threads(db, luis, page) == []
    assert len(await comments.threads(db, luis, page, include_resolved=True)) == 1
    with pytest.raises(Conflict):
        await comments.create(db, luis, page, body="Una más", thread_id=root.id)
    await comments.reopen(db, luis, root)
    assert root.resolved_at is None and len(await comments.threads(db, luis, page)) == 1


async def test_mentions_and_replies_notify_the_right_people(
    client: AsyncClient, db: AsyncSession, team: Team, page: FolioNode
) -> None:
    luis, ana = await _user(db, "luis"), await _user(db, "ana")
    vera, author = await _user(db, "vera"), await _user(db, team.instance.handle)
    root = await comments.create(db, luis, page, body="Revisa esto @ana y @vera, por favor")
    await comments.create(db, ana, page, body="Listo.", thread_id=root.id)
    await run_jobs(db)

    async def titles(user: User) -> list[str]:
        rows = await db.scalars(
            select(Notification.title)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at)
        )
        return list(rows)

    assert await titles(ana) == ["@luis mentioned you on 'Guía'"]  # once, not also as watcher
    assert await titles(vera) == ["@luis mentioned you on 'Guía'"]
    assert await titles(luis) == ["@ana replied in a thread on 'Guía'"]  # a participant
    assert await titles(author) == [  # the author follows the page
        "@luis commented on 'Guía'",
        "@ana replied in a thread on 'Guía'",
    ]
    # And what each title is built from, for the web app to write it in Spanish.
    params = await db.scalars(
        select(Notification.params)
        .where(Notification.user_id == author.id)
        .order_by(Notification.created_at)
    )
    assert list(params) == [
        {"actor": "@luis", "page": "Guía", "variant": "comment"},
        {"actor": "@ana", "page": "Guía", "variant": "reply"},
    ]


async def test_nobody_hears_about_a_page_they_cannot_see(
    client: AsyncClient, db: AsyncSession, team: Team, page: FolioNode
) -> None:
    body = {"view": [{"grantee_type": "user", "grantee": team.instance.handle}]}
    r = await client.put(
        f"{API}/nodes/{page.id}/restrictions", headers=team.instance.headers, json=body
    )
    assert r.status_code == 200
    author = await _user(db, team.instance.handle)
    await comments.create(db, author, page, body="Solo para mí, @luis")
    await run_jobs(db)
    luis = await _user(db, "luis")
    assert await db.scalar(select(Notification).where(Notification.user_id == luis.id)) is None


async def test_errors_and_permissions(
    client: AsyncClient, db: AsyncSession, team: Team, page: FolioNode
) -> None:
    luis, ana = await _user(db, "luis"), await _user(db, "ana")
    admin = await _user(db, team.instance.handle)
    with pytest.raises(ValidationFailed, match="Write something"):
        await comments.create(db, luis, page, body="  ")
    with pytest.raises(ValidationFailed, match="is not in the page"):
        await comments.create(db, luis, page, body="x", inline=True, quote="no existe")
    with pytest.raises(ValidationFailed, match="needs the text"):
        await comments.create(db, luis, page, body="x", inline=True)
    mine = await comments.create(db, luis, page, body="Mío")
    with pytest.raises(Forbidden):
        await comments.edit(db, ana, mine, "Ajeno")
    with pytest.raises(Forbidden):
        await comments.delete(db, ana, mine)
    edited = await comments.edit(db, luis, mine, "Mío, editado")
    assert comments.body_md(edited) == "Mío, editado" and edited.edited_at is not None
    await comments.delete(db, admin, mine)  # space admins delete any
    assert await comments.threads(db, luis, page) == []
    await _everyone_may(client, team, ["view"])  # the default for a new space
    with pytest.raises(Forbidden, match="comment permission"):
        await comments.create(db, luis, page, body="¿Puedo?")
