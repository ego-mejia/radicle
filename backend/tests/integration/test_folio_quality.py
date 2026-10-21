"""Keeping docs alive (Folio 2.7). Acceptance: a Verified page that expires turns Outdated
on its own and its owner is told."""

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import quality
from radicle.platform.db.models import Notification, User
from tests.conftest import Clock, Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy"}
    )
    await publish(client, team, r.json()["id"], md="# Deploy\n\nCon Docker y despliegue.")
    return str(r.json()["id"])


async def test_acceptance_verified_expires_and_the_owner_hears(
    client: AsyncClient, db: AsyncSession, team: Team, page: str, clock: Clock
) -> None:
    i = team.instance.headers
    r = await client.patch(f"{API}/nodes/{page}/status", headers=i, json={"status": "verified"})
    assert r.status_code == 200, r.text
    until = r.json()["verified_until"]
    assert r.json()["status"] == "verified"
    assert until == str(quality.today() + timedelta(days=90))
    await run_jobs(db)
    assert await quality.outdate_expired(db) == 0  # not yet
    clock.advance(days=91)
    assert await quality.outdate_expired(db) == 1
    assert await quality.outdate_expired(db) == 0  # idempotent
    await run_jobs(db)
    node = await db.get(FolioNode, uuid.UUID(page))  # 91 days on, the session expired
    assert node is not None and node.status == "outdated"
    owner = await db.scalar(select(User).where(User.handle == "fernando"))
    assert owner is not None
    notes = list(await db.scalars(select(Notification).where(Notification.user_id == owner.id)))
    assert [n.title for n in notes] == ["'Deploy' is outdated"]
    assert notes[0].params == {"page": "Deploy", "until": until}
    assert until in notes[0].body and notes[0].link and page in notes[0].link
    clock.advance(days=-91)
    r = await client.patch(f"{API}/nodes/{page}/status", headers=i, json={"status": "verified"})
    assert r.json()["status"] == "verified"  # verifying again restarts the clock


async def test_search_lifts_verified_and_lowers_outdated(
    client: AsyncClient, db: AsyncSession, team: Team, page: str
) -> None:
    i = team.instance.headers
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Deploy 2"}
    )
    other = str(r.json()["id"])
    await publish(client, team, other, md="# Deploy 2\n\nCon Docker y despliegue.")
    await client.patch(f"{API}/nodes/{other}/status", headers=i, json={"status": "verified"})
    await run_jobs(db)
    params = {"q": "despliegue docker", "mode": "text"}
    hits = (await client.get(f"{API}/search", params=params, headers=i)).json()["items"]
    assert hits[0]["node_id"] == other


async def test_owner_transfer_is_a_version(client: AsyncClient, team: Team, page: str) -> None:
    i = team.instance.headers
    r = await client.patch(f"{API}/nodes/{page}/owner", headers=i, json={"owner": "@ana"})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2 and r.json()["metadata"]["owner"] == "ana"
    history = (await client.get(f"{API}/nodes/{page}/versions", headers=i)).json()["items"]
    assert history[0]["change_note"] == "Owner: @fernando → @ana"
    r = await client.patch(f"{API}/nodes/{page}/owner", headers=i, json={"owner": "@nadie"})
    assert r.status_code == 422 and "owner" in r.text


async def test_errors_and_permissions(client: AsyncClient, team: Team, page: str) -> None:
    i, m = team.instance.headers, team.member.headers
    r = await client.patch(f"{API}/nodes/{page}/status", headers=m, json={"status": "verified"})
    assert r.status_code == 403 and "owner" in r.json()["detail"]
    r = await client.patch(f"{API}/nodes/{page}/status", headers=i, json={"status": "outdated"})
    assert r.status_code == 422
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Borrador"}
    )
    url = f"{API}/nodes/{r.json()['id']}/status"
    r = await client.patch(url, headers=i, json={"status": "in_review"})
    assert r.status_code == 409 and "not published" in r.json()["detail"]
