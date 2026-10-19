from httpx import AsyncClient

from tests.conftest import Team, bearer_for_new_human

API = "/api/v1/projects/PA/members"


async def test_list_members(client: AsyncClient, team: Team) -> None:
    r = await client.get(API, headers=team.viewer.headers)
    rows = {m["handle"]: (m["role"], m["kind"]) for m in r.json()["items"]}
    assert rows == {
        "agent-backend": ("member", "agent"),
        "ana": ("admin", "human"),
        "fernando": ("admin", "human"),
        "luis": ("member", "human"),
        "vera": ("viewer", "human"),
    }


async def test_change_role_and_remove(client: AsyncClient, team: Team) -> None:
    r = await client.put(f"{API}/luis", headers=team.admin.headers, json={"role": "viewer"})
    assert r.status_code == 200 and r.json()["role"] == "viewer"
    r = await client.delete(f"{API}/luis", headers=team.admin.headers)
    assert r.status_code == 204
    r = await client.get("/api/v1/projects/PA", headers=team.member.headers)
    assert r.status_code == 404


async def test_cannot_leave_project_without_admin(client: AsyncClient, team: Team) -> None:
    assert (await client.delete(f"{API}/fernando", headers=team.admin.headers)).status_code == 204
    r = await client.put(f"{API}/ana", headers=team.admin.headers, json={"role": "member"})
    assert r.status_code == 409
    assert "without an admin" in r.json()["detail"]
    r = await client.delete(f"{API}/ana", headers=team.admin.headers)
    assert r.status_code == 409


async def test_member_errors(client: AsyncClient, team: Team) -> None:
    r = await client.put(f"{API}/ghost", headers=team.admin.headers, json={"role": "member"})
    assert r.status_code == 404
    r = await client.put(f"{API}/olga", headers=team.admin.headers, json={"role": "owner"})
    assert r.status_code == 422
    r = await client.delete(f"{API}/olga", headers=team.admin.headers)
    assert r.status_code == 422
    assert "not a member" in r.json()["detail"]


async def test_inactive_users_cannot_join(client: AsyncClient, team: Team) -> None:
    await bearer_for_new_human(client, team.instance, "ines")
    await client.patch(
        "/api/v1/users/ines", headers=team.instance.headers, json={"is_active": False}
    )
    r = await client.put(f"{API}/ines", headers=team.admin.headers, json={"role": "member"})
    assert r.status_code == 422
