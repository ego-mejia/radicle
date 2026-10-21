"""Folio's notifications (Folio 2.4): publication to watchers, mentions on publish, and
agent submissions to Folio admins; never the actor, never someone who can't see the page."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import notices
from radicle.platform.db.models import Notification, User
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, agent_can_write, agent_submits, publish


async def _titles(db: AsyncSession, handle: str) -> list[str]:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    rows = await db.scalars(
        select(Notification.title)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at)
    )
    return list(rows)


async def _name(db: AsyncSession, handle: str) -> str:
    return str(await db.scalar(select(User.display_name).where(User.handle == handle)))


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    return str(r.json()["id"])


def test_mentions_are_found_anywhere_in_the_document() -> None:
    mention = {"type": "mention", "attrs": {"handle": "@Ana"}}
    doc = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [mention]},
            {"type": "table", "content": [{"type": "mention", "attrs": {"handle": "luis"}}]},
        ],
    }
    assert notices.mentions(doc) == {"ana", "luis"}
    assert notices.mentions(None) == set()


async def test_watchers_hear_about_a_publication(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    await publish(client, team, page, md="Hola")  # readers see it from v1 on
    await run_jobs(db)
    r = await client.put(f"{API}/watch/node/{page}", headers=team.member.headers)
    assert r.status_code == 204
    i = team.instance.headers
    await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"content_md": "Hola 2"})
    r = await client.post(f"{API}/nodes/{page}/publish", headers=i, json={"change_note": "v2"})
    assert r.status_code == 201, r.text
    await run_jobs(db)
    author = await _name(db, team.instance.handle)
    assert await _titles(db, team.member.handle) == [f"{author} published 'Deploy' (v2)"]
    assert await _titles(db, team.instance.handle) == []  # the author, who follows it


async def test_space_watchers_hear_too(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    space = (await client.get(f"{API}/spaces/docs", headers=team.member.headers)).json()
    r = await client.put(f"{API}/watch/space/{space['id']}", headers=team.member.headers)
    assert r.status_code == 204
    await publish(client, team, page, md="Hola")
    await run_jobs(db)
    assert len(await _titles(db, team.member.handle)) == 1


async def test_mentions_on_publish_once(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    md = f"Revisa esto @{team.member.handle}."
    await publish(client, team, page, md=md)
    await run_jobs(db)
    mentioned = [t for t in await _titles(db, team.member.handle) if "mentioned" in t]
    assert mentioned == [f"{await _name(db, team.instance.handle)} mentioned you in 'Deploy'"]
    # Publishing again with the same mention doesn't tell them twice.
    i = team.instance.headers
    r = await client.put(f"{API}/nodes/{page}/draft", headers=i, json={"content_md": md + " Ya."})
    assert r.status_code == 200
    r = await client.post(f"{API}/nodes/{page}/publish", headers=i, json={})
    assert r.status_code == 201, r.text
    await run_jobs(db)
    assert len([t for t in await _titles(db, team.member.handle) if "mentioned" in t]) == 1


async def test_restricted_pages_tell_nobody_outside(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    space = (await client.get(f"{API}/spaces/docs", headers=team.member.headers)).json()
    await client.put(f"{API}/watch/space/{space['id']}", headers=team.member.headers)
    r = await client.put(
        f"{API}/nodes/{page}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200, r.text
    await publish(client, team, page, md=f"Secreto para @{team.member.handle}")
    await run_jobs(db)
    assert await _titles(db, team.member.handle) == []


async def test_folio_admins_hear_about_agent_submissions(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Eng"})
    await agent_can_write(client, team, "eng")
    submission = await agent_submits(client, team, "eng", "Resumen semanal")
    await run_jobs(db)
    agent = await _name(db, team.agent.handle)
    assert await _titles(db, team.instance.handle) == [
        f"{agent} sent 'Resumen semanal' for approval"
    ]
    assert await _titles(db, team.member.handle) == []  # a reader, not a Folio admin
    # Approving publishes it: the agent follows what it created, so it hears about it.
    r = await client.post(f"{API}/submissions/{submission['id']}/approve", headers=i, json={})
    assert r.status_code == 201, r.text
    await run_jobs(db)
    assert any("published 'Resumen semanal'" in t for t in await _titles(db, team.agent.handle))
