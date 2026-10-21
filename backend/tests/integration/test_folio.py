"""Folio's skeleton (Folio 0.5): health, effective global role, and the admin grants."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditApp, AuditEntry
from radicle.platform.services import groups
from tests.conftest import Team

API = "/api/v1/folio"


@pytest.fixture(autouse=True)
def fresh_group_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups, "_cache", {})


async def _grants(client: AsyncClient, team: Team) -> list[dict]:
    r = await client.get(f"{API}/admin/grants", headers=team.instance.headers)
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def test_health_and_default_reader(client: AsyncClient, board: Team) -> None:
    assert (await client.get(f"{API}/health")).json() == {"status": "ok"}
    r = await client.get(f"{API}/me", headers=board.member.headers)
    assert r.status_code == 200 and r.json()["role"] == "reader"
    assert r.json()["handle"] == "luis"
    r = await client.get(f"{API}/me", headers=board.instance.headers)
    assert r.json()["role"] == "admin"
    assert [(g["grantee_type"], g["role"]) for g in await _grants(client, board)] == [
        ("everyone", "reader")
    ]


async def test_group_role_reaches_its_members(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo-docs"})
    await client.put("/api/v1/groups/equipo-docs/members/luis", headers=i)
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "group", "grantee": "equipo-docs", "role": "creator"},
    )
    assert r.status_code == 201, r.text
    assert (await client.get(f"{API}/me", headers=board.member.headers)).json()["role"] == "creator"
    assert (await client.get(f"{API}/me", headers=board.viewer.headers)).json()["role"] == "reader"

    # Setting the same grantee again replaces its role instead of adding a grant.
    await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "group", "grantee": "equipo-docs", "role": "admin"},
    )
    grants = await _grants(client, board)
    assert [(g["grantee"], g["role"]) for g in grants] == [
        (None, "reader"),
        ("equipo-docs", "admin"),
    ]


async def test_without_any_grant_folio_is_hidden(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    everyone = (await _grants(client, board))[0]
    r = await client.delete(f"{API}/admin/grants/{everyone['id']}", headers=i)
    assert r.status_code == 204
    r = await client.get(f"{API}/me", headers=board.member.headers)
    assert r.status_code == 404 and "no access to Folio" in r.json()["detail"]

    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": "@luis", "role": "creator"},
    )
    assert r.status_code == 201 and r.json()["grantee"] == "luis"
    assert (await client.get(f"{API}/me", headers=board.member.headers)).json()["role"] == "creator"
    assert (await client.get(f"{API}/me", headers=board.viewer.headers)).status_code == 404


async def test_grant_changes_are_audited_as_folio(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    i = board.instance.headers
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": "vera", "role": "admin"},
    )
    await client.delete(f"{API}/admin/grants/{r.json()['id']}", headers=i)
    entries = list(
        await db.scalars(select(AuditEntry).where(AuditEntry.action.startswith("folio.")))
    )
    assert [e.action for e in entries] == ["folio.grant_set", "folio.grant_remove"]
    assert all(e.app == AuditApp.folio for e in entries)


async def test_actionable_errors(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    r = await client.post(
        f"{API}/admin/grants", headers=i, json={"grantee_type": "group", "role": "reader"}
    )
    assert r.status_code == 422 and "group" in r.json()["detail"]
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "everyone", "grantee": "luis", "role": "reader"},
    )
    assert r.status_code == 422
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": "nobody", "role": "reader"},
    )
    assert r.status_code == 404
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": "x", "role": "god"},
    )
    assert r.status_code == 422
    r = await client.delete(f"{API}/admin/grants/00000000-0000-0000-0000-000000000001", headers=i)
    assert r.status_code == 404


async def test_only_folio_admins_manage_grants(client: AsyncClient, board: Team) -> None:
    member = board.member.headers
    r = await client.get(f"{API}/admin/grants", headers=member)
    assert r.status_code == 403 and "reader" in r.json()["detail"]
    r = await client.post(
        f"{API}/admin/grants",
        headers=member,
        json={"grantee_type": "user", "grantee": "luis", "role": "admin"},
    )
    assert r.status_code == 403
    anonymous = AsyncClient(transport=client._transport, base_url="http://test")
    assert (await anonymous.get(f"{API}/me")).status_code == 401
