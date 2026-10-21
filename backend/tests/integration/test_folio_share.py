"""Sharing a page with a message (Folio 2.4)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import Notification, User
from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish


async def _inbox(db: AsyncSession, handle: str) -> list[tuple[str, str]]:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    rows = await db.execute(
        select(Notification.title, Notification.body).where(Notification.user_id == user.id)
    )
    return [(t, b) for t, b in rows.all()]


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    await publish(client, team, r.json()["id"])
    return str(r.json()["id"])


async def test_share_with_people_and_groups(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i = team.instance.headers
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo"})
    await client.put(f"/api/v1/groups/equipo/members/{team.viewer.handle}", headers=i)
    body = {"users": [f"@{team.member.handle}"], "groups": ["equipo"], "message": "Léela hoy"}
    r = await client.post(f"{API}/nodes/{page}/share", headers=i, json=body)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "notified": sorted([team.member.handle, team.viewer.handle]),
        "cannot_see": [],
        "granted": [],
    }
    await run_jobs(db)
    sharer = await db.scalar(select(User.display_name).where(User.handle == team.instance.handle))
    assert await _inbox(db, team.member.handle) == [
        (f"{sharer} shared 'Deploy' with you", "Léela hoy")
    ]
    assert len(await _inbox(db, team.viewer.handle)) == 1
    assert await _inbox(db, team.instance.handle) == []


async def test_restricted_pages_and_granting_view(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.put(
        f"{API}/nodes/{page}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200
    body = {"users": [team.member.handle], "message": "Mira"}
    r = await client.post(f"{API}/nodes/{page}/share", headers=i, json=body)
    assert r.json() == {"notified": [], "cannot_see": [team.member.handle], "granted": []}
    await run_jobs(db)
    assert await _inbox(db, team.member.handle) == []

    r = await client.post(f"{API}/nodes/{page}/share", headers=i, json=body | {"grant_view": True})
    assert r.json()["granted"] == [team.member.handle]
    assert r.json()["notified"] == [team.member.handle]
    await run_jobs(db)
    assert len(await _inbox(db, team.member.handle)) == 1
    assert (await client.get(f"{API}/nodes/{page}", headers=m)).status_code == 200


async def test_a_restriction_from_above_cannot_be_granted_here(
    client: AsyncClient, team: Team, page: str
) -> None:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes",
        headers=i,
        json={"space": "docs", "kind": "page", "title": "Hija", "parent": page},
    )
    child = r.json()["id"]
    await publish(client, team, child)
    await client.put(
        f"{API}/nodes/{page}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    body = {"users": [team.member.handle], "grant_view": True}
    r = await client.post(f"{API}/nodes/{child}/share", headers=i, json=body)
    assert r.status_code == 403 and "page above it" in r.json()["detail"]


async def test_errors(client: AsyncClient, team: Team, page: str) -> None:
    m = team.member.headers
    r = await client.post(f"{API}/nodes/{page}/share", headers=m, json={"message": "x"})
    assert r.status_code == 422 and "at least one" in r.json()["detail"]
    r = await client.post(f"{API}/nodes/{page}/share", headers=m, json={"users": ["nadie"]})
    assert r.status_code == 404
    r = await client.post(f"{API}/nodes/{page}/share", headers=m, json={"groups": ["nada"]})
    assert r.status_code == 404
    long = {"users": ["ana"], "message": "x" * 2001}
    assert (await client.post(f"{API}/nodes/{page}/share", headers=m, json=long)).status_code == 422
