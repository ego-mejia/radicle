"""Settings → Members suggests people, agents and groups that are not in the project yet."""

from httpx import AsyncClient

from tests.conftest import Team

API = "/api/v1"


async def candidates(client: AsyncClient, team: Team, q: str = "") -> dict:
    r = await client.get(
        f"{API}/projects/PA/member-candidates", headers=team.admin.headers, params={"q": q}
    )
    assert r.status_code == 200, r.text
    return r.json()


async def test_suggests_who_is_not_in_the_project(client: AsyncClient, board: Team) -> None:
    i = board.instance.headers
    await client.post(
        f"{API}/users",
        headers=i,
        json={
            "handle": "nora",
            "display_name": "Nora Díaz",
            "email": "nora@example.com",
            "password": "temporary-pass",
        },
    )
    await client.post(f"{API}/groups", headers=i, json={"name": "legal", "description": "Abogados"})
    await client.post(f"{API}/groups", headers=i, json={"name": "backend"})
    await client.put(f"{API}/projects/PA/group-roles/backend", headers=i, json={"role": "member"})

    found = await candidates(client, board)
    handles = {p["handle"] for p in found["people"]}
    assert "nora" in handles
    members = (await client.get(f"{API}/projects/PA/members", headers=i)).json()["items"]
    assert not handles & {m["handle"] for m in members}
    assert "system" not in handles
    assert [g["name"] for g in found["groups"]] == ["legal"]

    # Search by name, handle or email; a leading @ is fine.
    assert [p["handle"] for p in (await candidates(client, board, "díaz"))["people"]] == ["nora"]
    assert [p["handle"] for p in (await candidates(client, board, "@nor"))["people"]] == ["nora"]
    assert [g["name"] for g in (await candidates(client, board, "abog"))["groups"]] == ["legal"]
    assert await candidates(client, board, "zzz") == {"people": [], "groups": []}


async def test_only_who_manages_members(client: AsyncClient, board: Team) -> None:
    r = await client.get(f"{API}/projects/PA/member-candidates", headers=board.member.headers)
    assert r.status_code == 403
    r = await client.get(f"{API}/projects/PA/member-candidates", headers=board.outsider.headers)
    assert r.status_code == 404
