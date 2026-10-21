"""Space grants and page restrictions over REST (Folio 1.4), with the permission matrix."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditEntry
from radicle.platform.services import groups
from tests.conftest import Team
from tests.integration.folio_helpers import API, publish


@pytest.fixture(autouse=True)
def fresh_group_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(groups, "_cache", {})


@pytest.fixture
async def docs(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    await client.post("/api/v1/groups", headers=i, json={"name": "equipo-docs"})
    await client.put("/api/v1/groups/equipo-docs/members/luis", headers=i)
    page = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    await publish(client, team, page.json()["id"])
    return page.json()


async def _give_docs_team_creator(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "group", "grantee": "equipo-docs", "role": "creator"},
    )
    r = await client.put(
        f"{API}/spaces/docs/grants",
        headers=i,
        json={
            "grants": [
                {"grantee_type": "everyone", "permissions": ["view"]},
                {
                    "grantee_type": "group",
                    "grantee": "equipo-docs",
                    "permissions": ["view", "create", "delete_own"],
                },
                {"grantee_type": "user", "grantee": "fernando", "permissions": ["admin"]},
            ]
        },
    )
    assert r.status_code == 200, r.text


async def test_acceptance_only_the_docs_team_writes(
    client: AsyncClient, db: AsyncSession, team: Team, docs: dict
) -> None:
    await _give_docs_team_creator(client, team)
    body = {"space": "docs", "kind": "page", "title": "Nueva"}
    luis, vera = team.member.headers, team.viewer.headers
    assert (await client.post(f"{API}/nodes", headers=luis, json=body)).status_code == 201
    r = await client.post(f"{API}/nodes", headers=vera, json=body)
    assert r.status_code == 403 and "create permission" in r.json()["detail"]
    assert (await client.get(f"{API}/nodes/{docs['id']}", headers=vera)).status_code == 200
    grants = (await client.get(f"{API}/spaces/docs/grants", headers=team.instance.headers)).json()
    assert [g["grantee"] for g in grants["grants"]] == [None, "equipo-docs", "fernando"]
    entry = await db.scalar(
        select(AuditEntry).where(AuditEntry.action == "folio.space_grants_change")
    )
    assert entry is not None and entry.app.value == "folio"


async def test_restrict_a_page_to_a_group(client: AsyncClient, team: Team, docs: dict) -> None:
    i = team.instance.headers
    url = f"{API}/nodes/{docs['id']}/restrictions"
    r = await client.put(
        url,
        headers=i,
        json={
            "view": [
                {"grantee_type": "group", "grantee": "equipo-docs"},
                {"grantee_type": "user", "grantee": "fernando"},
            ],
            "edit": [{"grantee_type": "user", "grantee": "fernando"}],
        },
    )
    assert r.status_code == 200, r.text
    assert [g["grantee"] for g in r.json()["view"]] == ["equipo-docs", "fernando"]
    assert (
        await client.get(f"{API}/nodes/{docs['id']}", headers=team.member.headers)
    ).status_code == 200
    assert (
        await client.get(f"{API}/nodes/{docs['id']}", headers=team.viewer.headers)
    ).status_code == 404
    r = await client.put(url, headers=i, json={"view": [], "edit": []})
    assert r.json() == {"view": [], "edit": []}
    assert (
        await client.get(f"{API}/nodes/{docs['id']}", headers=team.viewer.headers)
    ).status_code == 200


async def test_actionable_errors(client: AsyncClient, team: Team, docs: dict) -> None:
    i = team.instance.headers
    url = f"{API}/spaces/docs/grants"
    only_view = {"grants": [{"grantee_type": "everyone", "permissions": ["view"]}]}
    r = await client.put(url, headers=i, json=only_view)
    assert r.status_code == 422 and "admin" in r.json()["detail"]
    twice = {
        "grants": [{"grantee_type": "user", "grantee": "fernando", "permissions": ["admin"]}] * 2
    }
    assert (await client.put(url, headers=i, json=twice)).status_code == 422
    r = await client.put(
        url,
        headers=i,
        json={"grants": [{"grantee_type": "user", "grantee": "fernando", "permissions": ["fly"]}]},
    )
    assert r.status_code == 422
    r = await client.put(
        url,
        headers=i,
        json={"grants": [{"grantee_type": "group", "grantee": "nope", "permissions": ["admin"]}]},
    )
    assert r.status_code == 404
    mine = (await client.get(f"{API}/me/personal-space", headers=i)).json()["key"]
    r = await client.put(f"{API}/spaces/{mine}/grants", headers=i, json=only_view)
    assert r.status_code == 422 and "Personal spaces" in r.json()["detail"]
    rurl = f"{API}/nodes/{docs['id']}/restrictions"
    r = await client.put(rurl, headers=i, json={"view": [{"grantee_type": "everyone"}]})
    assert r.status_code == 422 and "everyone means no restriction" in r.json()["detail"]


async def test_you_cannot_lock_yourself_out(client: AsyncClient, team: Team, docs: dict) -> None:
    await _give_docs_team_creator(client, team)
    r = await client.put(
        f"{API}/nodes/{docs['id']}/restrictions",
        headers=team.member.headers,
        json={"view": [{"grantee_type": "user", "grantee": "vera"}]},
    )
    assert r.status_code == 422 and "Include yourself" in r.json()["detail"]
    assert (
        await client.get(f"{API}/nodes/{docs['id']}", headers=team.member.headers)
    ).status_code == 200


@pytest.mark.parametrize(
    ("who", "status"),
    [("member", 403), ("viewer", 403), ("agent", 403)],
)
async def test_only_space_admins_manage_sharing(
    client: AsyncClient, team: Team, docs: dict, who: str, status: int
) -> None:
    headers = team.by_role(who).headers
    assert (await client.get(f"{API}/spaces/docs/grants", headers=headers)).status_code == status
    r = await client.put(f"{API}/spaces/docs/grants", headers=headers, json={"grants": []})
    assert r.status_code == status
    r = await client.put(f"{API}/nodes/{docs['id']}/restrictions", headers=headers, json={})
    assert r.status_code == status
