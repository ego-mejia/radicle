"""Every permission of the catalog, for member and viewer, directly and through a group,
with the default and with an override. Admins always may; 403 names the permission."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest
from httpx import AsyncClient, Response

from radicle.docket.core.permissions import CATALOG, PERMISSIONS
from tests.conftest import Actor, Team, bearer_for_new_human, make_project, new_ticket
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


@dataclass
class World:
    team: Team
    actor: Actor
    ticket: str
    scrum: str


Action = Callable[[AsyncClient, World], Awaitable[Response]]


async def _admin_comment(c: AsyncClient, w: World) -> str:
    r = await c.post(
        f"{API}/tickets/{w.ticket}/comments",
        headers=w.team.admin.headers,
        json={"body_md": "del admin"},
    )
    return str(r.json()["id"])


async def _admin_attachment(c: AsyncClient, w: World) -> str:
    r = await c.post(
        f"{API}/tickets/{w.ticket}/attachments",
        headers=w.team.admin.headers,
        files={"file": ("a.txt", b"hola", "text/plain")},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _admin_worklog(c: AsyncClient, w: World) -> str:
    r = await c.post(
        f"{API}/tickets/{w.ticket}/worklogs", headers=w.team.admin.headers, json={"minutes": 30}
    )
    return str(r.json()["id"])


async def _bulk(c: AsyncClient, w: World) -> Response:
    r = await c.post(
        f"{API}/tickets/bulk",
        headers=w.actor.headers,
        json={"keys": [w.ticket], "operations": [{"op": "add_tag", "tag": "x"}]},
    )
    # Bulk reports per ticket; turn a denied ticket into the 403 it carries.
    if r.status_code == 200 and r.json()["failed"]:
        return Response(403, json={"detail": r.json()["results"][0]["error"]})
    return r


async def _edit(c: AsyncClient, w: World) -> Response:
    t = (await c.get(f"{API}/tickets/{w.ticket}", headers=w.team.admin.headers)).json()
    return await c.patch(
        f"{API}/tickets/{w.ticket}",
        headers={**w.actor.headers, "If-Match": str(t["version"])},
        json={"title": "Otro título"},
    )


ACTIONS: dict[str, Action] = {
    "ticket.create": lambda c, w: c.post(
        f"{API}/projects/PA/tickets",
        headers=w.actor.headers,
        json={"type": "draft", "classification": "idea", "title": "Nuevo"},
    ),
    "ticket.edit": _edit,
    "ticket.transition": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/transitions",
        headers=w.actor.headers,
        json={"to_status": "In Progress"},
    ),
    "ticket.delete": lambda c, w: c.delete(f"{API}/tickets/{w.ticket}", headers=w.actor.headers),
    "ticket.move": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/move", headers=w.actor.headers, json={"target_project": "PB"}
    ),
    "ticket.bulk_edit": _bulk,
    "ticket.set_security": lambda c, w: c.get(
        f"{API}/projects/PA/permissions", headers=w.actor.headers
    ),
    "comment.create": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/comments", headers=w.actor.headers, json={"body_md": "hola"}
    ),
    "comment.delete_any": lambda c, w: _then(
        _admin_comment, lambda i: c.delete(f"{API}/comments/{i}", headers=w.actor.headers), c, w
    ),
    "attachment.upload": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/attachments",
        headers=w.actor.headers,
        files={"file": ("b.txt", b"x", "text/plain")},
    ),
    "attachment.delete_any": lambda c, w: _then(
        _admin_attachment,
        lambda i: c.delete(f"{API}/attachments/{i}", headers=w.actor.headers),
        c,
        w,
    ),
    "worklog.create": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/worklogs", headers=w.actor.headers, json={"minutes": 15}
    ),
    "worklog.edit_any": lambda c, w: _then(
        _admin_worklog,
        lambda i: c.patch(f"{API}/worklogs/{i}", headers=w.actor.headers, json={"minutes": 45}),
        c,
        w,
    ),
    "vote": lambda c, w: c.put(f"{API}/tickets/{w.ticket}/vote", headers=w.actor.headers),
    "link.manage": lambda c, w: c.post(
        f"{API}/tickets/{w.ticket}/links",
        headers=w.actor.headers,
        json={"type": "relates_to", "target": "PA-2"},
    ),
    "sprint.manage": lambda c, w: c.post(
        f"{API}/boards/{w.scrum}/sprints", headers=w.actor.headers, json={}
    ),
    "board.manage": lambda c, w: c.post(
        f"{API}/projects/PA/boards", headers=w.actor.headers, json={"name": "Otro"}
    ),
    "inbox.triage": lambda c, w: c.get(f"{API}/projects/PA/permissions", headers=w.actor.headers),
    "project.settings": lambda c, w: c.patch(
        f"{API}/projects/PA", headers=w.actor.headers, json={"name": "Proyecto A"}
    ),
    "members.manage": lambda c, w: c.put(
        f"{API}/projects/PA/members/olga", headers=w.actor.headers, json={"role": "viewer"}
    ),
}
# Wired in later deliverables (security levels, inbox); exercised by their own tests.
LATER = {"ticket.set_security", "inbox.triage"}


async def _then(setup, act, c: AsyncClient, w: World) -> Response:  # type: ignore[no-untyped-def]
    return await act(await setup(c, w))


def test_every_permission_has_an_action() -> None:
    assert set(ACTIONS) == set(PERMISSIONS)


CASES = [
    (perm, role, via, override)
    for perm in PERMISSIONS
    if perm not in LATER
    for role in ("member", "viewer")
    for via, override in (("direct", False), ("group", True))
]


@pytest.mark.parametrize(("perm", "role", "via", "override"), CASES)
async def test_permission(
    client: AsyncClient, board: Team, perm: str, role: str, via: str, override: bool
) -> None:
    team = board
    await make_project(client, team.instance, "PB")
    for actor in ("member", "viewer"):
        await client.put(
            f"{API}/projects/PB/members/{team.by_role(actor).handle}",
            headers=team.instance.headers,
            json={"role": "admin"},
        )
    await new_ticket(client, team.admin, title="Uno")
    await new_ticket(client, team.admin, title="Dos")
    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=team.admin.headers,
        json={"name": "Scrum", "kind": "scrum"},
    )
    scrum = r.json()["id"]

    if via == "direct":
        actor = team.by_role(role)
    else:
        actor = await bearer_for_new_human(client, team.instance, f"g{role}")
        await client.put(
            f"{API}/projects/PB/members/{actor.handle}",
            headers=team.instance.headers,
            json={"role": "admin"},
        )
        await client.post(f"{API}/groups", headers=team.instance.headers, json={"name": "equipo"})
        await client.put(
            f"{API}/groups/equipo/members/{actor.handle}", headers=team.instance.headers
        )
        r = await client.put(
            f"{API}/projects/PA/group-roles/equipo", headers=team.admin.headers, json={"role": role}
        )
        assert r.status_code == 200, r.text

    default = CATALOG[perm][0 if role == "member" else 1]
    expected = default
    if override:
        expected = not default
        r = await client.put(
            f"{API}/projects/PA/permissions",
            headers=team.admin.headers,
            json={role: {perm: expected}},
        )
        assert r.status_code == 200, r.text

    r = await ACTIONS[perm](client, World(team, actor, "PA-1", scrum))
    if expected:
        # Allowed: past the permission check (a business rule may still say no).
        assert r.status_code not in (403, 404), (perm, role, via, r.text)
    else:
        assert r.status_code == 403, (perm, role, via, r.text)
        assert f"'{perm}' permission is off for the {role} role" in r.json()["detail"]


async def test_effective_role_is_the_highest(client: AsyncClient, board: Team) -> None:
    await client.post(
        f"{API}/groups", headers=board.instance.headers, json={"name": "equipo-legal"}
    )
    await client.put(
        f"{API}/groups/equipo-legal/members/{board.viewer.handle}", headers=board.instance.headers
    )
    r = await client.put(
        f"{API}/projects/PA/group-roles/equipo-legal",
        headers=board.admin.headers,
        json={"role": "member"},
    )
    assert r.status_code == 200
    members = (await client.get(f"{API}/projects/PA/members", headers=board.viewer.headers)).json()
    vera = next(m for m in members["items"] if m["handle"] == board.viewer.handle)
    assert (vera["role"], vera["effective_role"], vera["groups"]) == (
        "viewer",
        "member",
        ["equipo-legal"],
    )
    me = (await client.get(f"{API}/me", headers=board.viewer.headers)).json()
    assert me["projects"][0]["role"] == "member"
    assert "ticket.create" in me["projects"][0]["permissions"]
    r = await new_ticket(client, board.viewer, title="Ahora sí")
    assert r["key"] == "PA-1"

    # Leaving the group takes the access away right away.
    await client.delete(
        f"{API}/groups/equipo-legal/members/{board.viewer.handle}", headers=board.instance.headers
    )
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=board.viewer.headers,
        json={"type": "draft", "classification": "idea", "title": "No"},
    )
    assert r.status_code == 403


async def test_group_only_members_see_the_project(client: AsyncClient, board: Team) -> None:
    outsider = board.outsider
    assert (await client.get(f"{API}/projects/PA", headers=outsider.headers)).status_code == 404
    await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "externos"})
    await client.put(
        f"{API}/groups/externos/members/{outsider.handle}", headers=board.instance.headers
    )
    await client.put(
        f"{API}/projects/PA/group-roles/externos",
        headers=board.admin.headers,
        json={"role": "viewer"},
    )
    assert (await client.get(f"{API}/projects/PA", headers=outsider.headers)).status_code == 200
    projects = (await client.get(f"{API}/projects", headers=outsider.headers)).json()["items"]
    assert [p["key"] for p in projects] == ["PA"]
    await new_ticket(client, board.member)
    r = await client.get(f"{API}/tickets", headers=outsider.headers, params={"q": "project = PA"})
    assert r.json()["total"] == 1


async def test_groups_and_matrix_admin_only(client: AsyncClient, board: Team) -> None:
    r = await client.post(f"{API}/groups", headers=board.admin.headers, json={"name": "x"})
    assert r.status_code == 403
    r = await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "a b"})
    assert r.status_code == 422
    r = await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "dev"})
    assert r.status_code == 201
    r = await client.post(f"{API}/groups", headers=board.instance.headers, json={"name": "DEV"})
    assert r.status_code == 409
    r = await client.put(
        f"{API}/projects/PA/group-roles/dev", headers=board.member.headers, json={"role": "admin"}
    )
    assert r.status_code == 403
    r = await client.put(
        f"{API}/projects/PA/permissions",
        headers=board.member.headers,
        json={"member": {"ticket.delete": True}},
    )
    assert r.status_code == 403
    r = await client.put(
        f"{API}/projects/PA/permissions",
        headers=board.admin.headers,
        json={"member": {"ticket.fly": True}},
    )
    assert r.status_code == 422 and "ticket.fly" in r.json()["detail"]
    r = await client.put(
        f"{API}/projects/PA/permissions",
        headers=board.admin.headers,
        json={"member": {"ticket.transition": False}},
    )
    row = next(x for x in r.json()["rows"] if x["permission"] == "ticket.transition")
    assert (row["member"], row["member_default"]) == (False, True)
    r = await client.delete(f"{API}/projects/PA/permissions", headers=board.admin.headers)
    row = next(x for x in r.json()["rows"] if x["permission"] == "ticket.transition")
    assert row["member"] is True


MCP_CASES = [
    (
        "ticket.create",
        "create_ticket",
        {"project": "PA", "type": "draft", "classification": "idea", "title": "x"},
    ),
    ("ticket.edit", "update_ticket", {"key": "PA-1", "changes": {"title": "Nuevo"}}),
    ("ticket.transition", "transition_ticket", {"key": "PA-1", "to_status": "In Progress"}),
    ("comment.create", "add_comment", {"key": "PA-1", "body": "hola"}),
    ("link.manage", "link_tickets", {"source": "PA-1", "type": "relates_to", "target": "PA-2"}),
    ("worklog.create", "log_work", {"key": "PA-1", "minutes": 30}),
]


@pytest.mark.parametrize(("perm", "tool", "args"), MCP_CASES)
async def test_mcp_follows_the_matrix(
    client: AsyncClient, board: Team, mcp_for: McpFor, perm: str, tool: str, args: dict
) -> None:
    await new_ticket(client, board.admin, title="Uno")
    await new_ticket(client, board.admin, title="Dos")
    r = await client.put(
        f"{API}/projects/PA/permissions",
        headers=board.admin.headers,
        json={"member": {perm: False}},
    )
    assert r.status_code == 200
    async with mcp_for(board.agent) as mcp:  # the agent is a member of PA
        result = await mcp.call_tool(tool, args)
        assert result.is_error
        assert f"'{perm}' permission is off for the member role" in error_text(result)
        me = payload(await mcp.call_tool("whoami"))
        assert perm not in me["projects"][0]["permissions"]
