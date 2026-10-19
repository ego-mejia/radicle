import pytest
from httpx import AsyncClient

from tests.conftest import Team, new_ticket

T = "/api/v1/tickets/PA-1"
ROLES = ["instance", "admin", "member", "viewer", "agent", "outsider"]
RANK = {"viewer": 0, "member": 1, "admin": 2}
ROLE_RANK = {"instance": 2, "admin": 2, "member": 1, "agent": 1, "viewer": 0}

ACTIONS = [
    ("GET", T, None, "viewer"),
    ("GET", f"{T}/history", None, "viewer"),
    ("GET", f"{T}/children", None, "viewer"),
    ("POST", "/api/v1/projects/PA/tickets", {"type": "draft", "title": "x"}, "member"),
    ("PATCH", T, {"title": "x", "expected_version": 1}, "member"),
    ("PATCH", f"{T}/checklist/0", {"checked": True}, "member"),
    ("PUT", f"{T}/collaborators/luis", None, "member"),
    ("DELETE", T, None, "admin"),
]


@pytest.mark.parametrize("who", ROLES)
@pytest.mark.parametrize(("method", "path", "body", "need"), ACTIONS)
async def test_ticket_permission_matrix(
    client: AsyncClient,
    board: Team,
    who: str,
    method: str,
    path: str,
    body: dict | None,
    need: str,
) -> None:
    await new_ticket(client, board.member, description_md="- [ ] uno")
    r = await client.request(method, path, headers=board.by_role(who).headers, json=body)
    if who == "outsider":
        assert r.status_code == 404, r.text
    elif ROLE_RANK[who] >= RANK[need]:
        assert r.status_code in (200, 201, 204), r.text
    else:
        assert r.status_code == 403, r.text


async def test_archived_project_tickets_are_read_only(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await client.post("/api/v1/projects/PA/archive", headers=board.admin.headers)
    assert (await client.get(T, headers=board.member.headers)).status_code == 200
    r = await client.patch(
        T, headers=board.member.headers, json={"title": "x", "expected_version": 1}
    )
    assert r.status_code == 409 and "archived" in r.json()["detail"]
    r = await client.post(
        "/api/v1/projects/PA/tickets",
        headers=board.member.headers,
        json={"type": "draft", "title": "x"},
    )
    assert r.status_code == 409
