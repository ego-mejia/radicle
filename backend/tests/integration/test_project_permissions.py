"""Permission matrix for project endpoints: every action against every role."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team

P = "/api/v1/projects/PA"
ROLES = ["instance", "admin", "member", "viewer", "agent", "outsider"]

# (method, path, body, minimum role) -- minimum: viewer < member < admin
ACTIONS = [
    ("GET", P, None, "viewer"),
    ("GET", f"{P}/workflows", None, "viewer"),
    ("GET", f"{P}/members", None, "viewer"),
    ("GET", f"{P}/areas", None, "viewer"),
    ("GET", f"{P}/milestones", None, "viewer"),
    ("PATCH", P, {"name": "Renamed"}, "admin"),
    ("POST", f"{P}/archive", None, "admin"),
    ("PUT", f"{P}/members/olga", {"role": "viewer"}, "admin"),
    ("POST", f"{P}/areas", {"name": "Legal"}, "admin"),
    ("POST", f"{P}/milestones", {"name": "V1"}, "admin"),
]
RANK = {"viewer": 0, "member": 1, "admin": 2}
ROLE_RANK = {"instance": 2, "admin": 2, "member": 1, "agent": 1, "viewer": 0}


@pytest.mark.parametrize("who", ROLES)
@pytest.mark.parametrize(("method", "path", "body", "need"), ACTIONS)
async def test_permission_matrix(
    client: AsyncClient, team: Team, who: str, method: str, path: str, body: dict | None, need: str
) -> None:
    actor = team.by_role(who)
    r = await client.request(method, path, headers=actor.headers, json=body)
    if who == "outsider":
        assert r.status_code == 404, r.text
        assert r.json()["detail"] == "Project PA not found."
    elif ROLE_RANK[who] >= RANK[need]:
        assert r.status_code in (200, 201), r.text
    else:
        assert r.status_code == 403, r.text
        detail = r.json()["detail"]
        assert "this action needs" in detail or "permission is off" in detail


async def test_area_and_milestone_edits_need_admin(client: AsyncClient, team: Team) -> None:
    await client.post(f"{P}/areas", headers=team.admin.headers, json={"name": "Legal"})
    await client.post(f"{P}/milestones", headers=team.admin.headers, json={"name": "V1"})
    for who in ("member", "viewer", "agent"):
        h = team.by_role(who).headers
        assert (
            await client.patch(f"{P}/areas/Legal", headers=h, json={"name": "L"})
        ).status_code == 403
        assert (await client.delete(f"{P}/areas/Legal", headers=h)).status_code == 403
        assert (
            await client.patch(f"{P}/milestones/V1", headers=h, json={"status": "closed"})
        ).status_code == 403
        assert (await client.delete(f"{P}/members/luis", headers=h)).status_code == 403
    h = team.outsider.headers
    assert (
        await client.patch(f"{P}/areas/Legal", headers=h, json={"name": "L"})
    ).status_code == 404
    assert (await client.get(f"{P}/milestones/V1", headers=h)).status_code == 404


async def test_unauthenticated_is_401(client: AsyncClient, team: Team) -> None:
    client.cookies.clear()
    assert (await client.get(P)).status_code == 401
