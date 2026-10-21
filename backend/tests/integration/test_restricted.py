"""Restricted tickets never leak. One test walks every GET route of the API and every MCP
tool; it fails when a new one appears without being covered here."""

import re

import pytest
from httpx import AsyncClient

from radicle.main import create_app
from tests.conftest import Actor, Team, bearer_for_new_human, make_project, new_ticket, patch_ticket
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"
SECRET = "SECRETO"  # in the restricted ticket's title, description, comment, file and worklog


def leaks(text: str) -> bool:
    return SECRET.lower() in text.lower() or re.search(r"\bPA-2\b", text) is not None


async def restrict(client: AsyncClient, team: Team, key: str, level: str = "Legal confidencial"):  # type: ignore[no-untyped-def]
    t = (await client.get(f"{API}/tickets/{key}", headers=team.admin.headers)).json()
    return await client.patch(
        f"{API}/tickets/{key}",
        headers={**team.admin.headers, "If-Match": str(t["version"])},
        json={"security_level": level},
    )


@pytest.fixture
async def world(client: AsyncClient, board: Team) -> dict:
    """PA-1 visible; PA-2 restricted (SECRETO) child of PA-1, blocking it, with a comment,
    a file and a worklog; PA-3 visible child of PA-2. A legal user sees PA-2 via the group."""
    team = board
    legal = await bearer_for_new_human(client, team.instance, "legal")
    await client.post(f"{API}/groups", headers=team.instance.headers, json={"name": "equipo-legal"})
    await client.put(f"{API}/groups/equipo-legal/members/legal", headers=team.instance.headers)
    r = await client.put(
        f"{API}/projects/PA/group-roles/equipo-legal",
        headers=team.admin.headers,
        json={"role": "member"},
    )
    assert r.status_code == 200, r.text
    r = await client.post(
        f"{API}/projects/PA/security-levels",
        headers=team.admin.headers,
        json={"name": "Legal confidencial", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    level = r.json()
    r = await client.put(
        f"{API}/security-levels/{level['id']}/grants",
        headers=team.admin.headers,
        json={"groups": ["equipo-legal"]},
    )
    assert r.json()["groups"] == ["equipo-legal"]

    await new_ticket(
        client,
        team.admin,
        title="Visible padre",
        milestone="V1",
        start_date="2026-11-02",
        due_date="2026-11-06",
        estimate_hours=3,
    )
    await new_ticket(
        client,
        team.admin,
        title=f"{SECRET} demanda",
        description_md=f"{SECRET}",
        parent="PA-1",
        milestone="V1",
        start_date="2026-11-02",
        due_date="2026-11-04",
        estimate_hours=5,
        tags=["legal"],
        assignee="luis",
    )
    await new_ticket(client, team.admin, title="Visible hijo", parent="PA-2")
    r = await client.post(
        f"{API}/tickets/PA-2/links",
        headers=team.admin.headers,
        json={"type": "blocks", "target": "PA-1"},
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        f"{API}/tickets/PA-2/comments",
        headers=team.admin.headers,
        json={"body_md": f"comentario {SECRET}"},
    )
    comment = r.json()["id"]
    r = await client.post(
        f"{API}/tickets/PA-2/attachments",
        headers=team.admin.headers,
        files={"file": ("secreto.txt", b"x", "text/plain")},
    )
    attachment = r.json()["id"]
    r = await client.post(
        f"{API}/tickets/PA-2/worklogs",
        headers=team.admin.headers,
        json={"minutes": 30, "description": SECRET},
    )
    worklog = r.json()["id"]
    r = await restrict(client, team, "PA-2")
    assert r.status_code == 200 and r.json()["security_level"] == "Legal confidencial", r.text

    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=team.admin.headers,
        json={"name": "Scrum", "kind": "scrum", "swimlane_by": "parent"},
    )
    scrum = r.json()
    r = await client.post(
        f"{API}/boards/{scrum['id']}/sprints", headers=team.admin.headers, json={}
    )
    sprint = r.json()
    await client.post(
        f"{API}/sprints/{sprint['id']}/tickets",
        headers=team.admin.headers,
        json={"keys": ["PA-1", "PA-2", "PA-3"]},
    )
    await client.post(
        f"{API}/sprints/{sprint['id']}/start",
        headers=team.admin.headers,
        json={"start_date": "2026-11-02", "end_date": "2026-11-13"},
    )
    main = (await client.get(f"{API}/projects/PA/boards", headers=team.admin.headers)).json()
    main_id = main["items"][0]["id"]
    r = await client.get(f"{API}/projects/PA/dashboard", headers=team.admin.headers)
    dashboard = r.json()
    r = await client.post(
        f"{API}/dashboards/{dashboard['id']}/widgets",
        headers=team.admin.headers,
        json={"widget_type": "filter_results", "title": "Todo", "config": {"rql": "project = PA"}},
    )
    widgets = [w["id"] for w in dashboard["widgets"]] + [r.json()["id"]]
    r = await client.post(
        f"{API}/filters", headers=team.member.headers, json={"name": "Todo", "rql": "project = PA"}
    )
    return {
        "legal": legal,
        "level": level,
        "comment": comment,
        "attachment": attachment,
        "worklog": worklog,
        "scrum": scrum["id"],
        "main": main_id,
        "sprint": sprint["id"],
        "dashboard": dashboard["id"],
        "widgets": widgets,
    }


# GET routes -> the URLs to try as a member outside the level. {x} come from the world.
COVERED: dict[str, list[str]] = {
    "/api/v1/tickets": [
        "/tickets?q=project = PA",
        "/tickets?q=key = PA-2",
        f"/tickets?q=text ~ {SECRET}",
        "/tickets?q=tag = legal",
    ],
    "/api/v1/tickets/{key}": ["/tickets/PA-1", "/tickets/PA-3"],
    "/api/v1/tickets/{key}/attachments": ["/tickets/PA-1/attachments"],
    "/api/v1/tickets/{key}/children": ["/tickets/PA-1/children"],
    "/api/v1/tickets/{key}/comments": ["/tickets/PA-1/comments"],
    "/api/v1/tickets/{key}/history": ["/tickets/PA-1/history", "/tickets/PA-3/history"],
    "/api/v1/tickets/{key}/links": ["/tickets/PA-1/links"],
    "/api/v1/tickets/{key}/transitions": ["/tickets/PA-1/transitions"],
    "/api/v1/tickets/{key}/voters": ["/tickets/PA-1/voters"],
    "/api/v1/tickets/{key}/worklogs": ["/tickets/PA-1/worklogs"],
    "/api/v1/attachments/{attachment_id}/content": [],  # 404 check below
    "/api/v1/boards/{board_id}": ["/boards/{main}"],
    "/api/v1/boards/{board_id}/backlog": ["/boards/{scrum}/backlog"],
    "/api/v1/boards/{board_id}/data": [
        "/boards/{main}/data",
        "/boards/{scrum}/data",
        "/boards/{main}/data?swimlane=parent",
    ],
    "/api/v1/boards/{board_id}/quick-filters": ["/boards/{main}/quick-filters"],
    "/api/v1/boards/{board_id}/sprints": ["/boards/{scrum}/sprints"],
    "/api/v1/sprints/{sprint_id}": ["/sprints/{sprint}"],
    "/api/v1/sprints/{sprint_id}/report": ["/sprints/{sprint}/report"],
    "/api/v1/projects/{key}/timeline": ["/projects/PA/timeline"],
    "/api/v1/projects/{key}/dashboard": ["/projects/PA/dashboard"],
    "/api/v1/dashboards": ["/dashboards"],
    "/api/v1/dashboards/{dashboard_id}": ["/dashboards/{dashboard}"],
    "/api/v1/widgets/{widget_id}/data": [],  # every widget, below
    "/api/v1/reports/{kind}": [
        "/reports/control_chart?project=PA",
        "/reports/time?project=PA",
        "/reports/sprint?sprint={sprint}",
        "/reports/burndown?sprint={sprint}",
        "/reports/distribution?project=PA&field=tag",
        "/reports/cfd?project=PA",
        "/reports/milestone_progress?project=PA&milestone=V1",
    ],
    "/api/v1/reports/{kind}.csv": [
        "/reports/time.csv?project=PA",
        "/reports/sprint.csv?sprint={sprint}",
    ],
    "/api/v1/projects/{key}": ["/projects/PA"],
    "/api/v1/projects/{key}/milestones": ["/projects/PA/milestones"],
    "/api/v1/projects/{key}/milestones/{name}": ["/projects/PA/milestones/V1"],
    "/api/v1/projects/{key}/milestones/{name}/recap": ["/projects/PA/milestones/V1/recap"],
    "/api/v1/filters": ["/filters"],
    "/api/v1/search/fields": ["/search/fields?project=PA"],
    "/api/v1/projects/{key}/inbox": ["/projects/PA/inbox", "/projects/PA/inbox?tab=approved"],
}
# Routes that never show ticket content (configuration, people, the user's own data).
EXEMPT = {
    "/api/v1/health",
    "/api/v1/version",
    "/api/v1/limits",
    "/api/v1/setup/status",
    "/api/v1/me",
    "/api/v1/me/preferences",
    # Only your own notifications; each app's resolver already left out what you can't see.
    "/api/v1/me/notifications",
    "/api/v1/me/notifications/stream",
    "/api/v1/me/notification-preferences",
    "/api/v1/me/tokens",
    "/api/v1/users",
    "/api/v1/users/{handle}",
    "/api/v1/users/{handle}/tokens",
    "/api/v1/groups",
    "/api/v1/groups/{name}",
    "/api/v1/jobs/{job_id}",
    "/api/v1/templates",
    "/api/v1/templates/{template_id}",
    "/api/v1/templates/{template_id}/sync-runs",
    "/api/v1/projects",
    "/api/v1/projects/{key}/areas",
    "/api/v1/projects/{key}/boards",
    "/api/v1/projects/{key}/fields",
    "/api/v1/projects/{key}/group-roles",
    "/api/v1/projects/{key}/members",
    "/api/v1/projects/{key}/permissions",
    "/api/v1/projects/{key}/schema",
    "/api/v1/projects/{key}/screens",
    "/api/v1/projects/{key}/security-levels",
    "/api/v1/projects/{key}/workflows",
    "/api/v1/projects/{key}/inbox-settings",
    "/api/v1/auth/options",
    "/api/v1/admin/sso-providers",
    "/api/v1/admin/settings",
    "/api/v1/audit",
    "/api/v1/audit.csv",
    "/api/v1/admin/assistant",
    "/api/v1/admin/ai",
    "/api/v1/folio/health",
    "/api/v1/folio/me",
    "/api/v1/folio/admin/grants",
    # Folio content: its own leak test comes with page restrictions (Folio 1.4).
    "/api/v1/folio/spaces",
    "/api/v1/folio/me/personal-space",
    "/api/v1/folio/spaces/{key}",
    "/api/v1/folio/spaces/{key}/tree",
    "/api/v1/folio/spaces/{key}/posts",
    "/api/v1/folio/nodes/{node_id}",
    "/api/v1/folio/nodes/{node_id}/draft",
    "/api/v1/folio/assets/{asset_id}",
    "/api/v1/folio/metadata-schema",
    "/api/v1/folio/nodes/{node_id}/versions",
    "/api/v1/folio/nodes/{node_id}/versions/{number}",
    "/api/v1/folio/nodes/{node_id}/diff",
    "/api/v1/folio/spaces/{key}/grants",
    "/api/v1/folio/nodes/{node_id}/restrictions",
    "/api/v1/folio/submissions",
    "/api/v1/folio/search",
    "/api/v1/folio/nodes/{node_id}/snapshots",
    "/api/v1/folio/nodes/{node_id}/snapshots/{snapshot_id}",
    "/api/v1/folio/home",
    "/api/v1/folio/nodes",
    "/api/v1/folio/templates",
    "/api/v1/folio/link-preview",
    "/api/v1/folio/templates/{template_id}",
    "/api/v1/folio/nodes/{node_id}/comments",
    "/api/v1/folio/people",
    "/api/v1/folio/spaces/{key}/archived",
    "/api/v1/folio/watch/{target_type}/{target_id}",
    "/api/v1/folio/reactions/{target_type}/{target_id}",
    "/api/v1/folio/me/recents",
    "/api/v1/folio/me/tasks",
    "/api/v1/folio/me/feed",
    "/api/v1/folio/me/favorites",
    "/api/v1/folio/submissions/{submission_id}",
    "/api/v1/folio/admin/{catalog}",
    "/api/v1/mcp/tools",
    "/api/v1/projects/{key}/member-candidates",
    "/api/v1/openapi.json",
}


def test_every_get_route_is_covered() -> None:
    routes = {p for p, ops in create_app().openapi()["paths"].items() if "get" in ops}
    missing = routes - set(COVERED) - EXEMPT
    assert not missing, f"Cover these GET routes in the restricted leak test: {sorted(missing)}"


async def test_nothing_leaks_through_get_routes(
    client: AsyncClient, board: Team, world: dict
) -> None:
    member = board.member  # luis: member of PA, outside the level, even its assignee
    for urls in COVERED.values():
        for template in urls:
            url = API + template.format(**world)
            r = await client.get(url, headers=member.headers)
            assert r.status_code == 200, (url, r.text)
            assert not leaks(r.text), (url, r.text[:500])
    for widget in world["widgets"]:
        r = await client.get(f"{API}/widgets/{widget}/data", headers=member.headers)
        assert r.status_code == 200 and not leaks(r.text), r.text[:300]

    # The restricted ticket and its parts are 404, never 403.
    for url in (
        "/tickets/PA-2",
        "/tickets/pa-2",
        "/tickets/PA-2/comments",
        "/tickets/PA-2/history",
        "/tickets/PA-2/links",
        "/tickets/PA-2/attachments",
        f"/attachments/{world['attachment']}/content",
    ):
        r = await client.get(API + url, headers=member.headers)
        assert r.status_code == 404, (url, r.text)
    r = await client.delete(f"{API}/comments/{world['comment']}", headers=board.member.headers)
    assert r.status_code == 404
    r = await client.patch(
        f"{API}/worklogs/{world['worklog']}", headers=member.headers, json={"minutes": 1}
    )
    assert r.status_code == 404

    # Links and the parent show as a restricted ticket, without key or title.
    t1 = (await client.get(f"{API}/tickets/PA-1", headers=member.headers)).json()
    assert t1["links"][0]["ticket"] == {
        "key": None,
        "title": None,
        "type": None,
        "status": None,
        "restricted": True,
    }
    assert t1["children_count"] == 0
    t3 = (await client.get(f"{API}/tickets/PA-3", headers=member.headers)).json()
    assert t3["parent"]["restricted"] is True
    # Aggregates still count it so numbers add up.
    progress = (
        await client.get(
            f"{API}/reports/milestone_progress",
            headers=member.headers,
            params={"project": "PA", "milestone": "V1"},
        )
    ).json()
    assert progress["summary"]["tickets"] == 2


async def test_grants_admins_and_participants(
    client: AsyncClient, board: Team, world: dict
) -> None:
    legal: Actor = world["legal"]
    for actor in (legal, board.admin, board.instance):
        r = await client.get(f"{API}/tickets/PA-2", headers=actor.headers)
        assert r.status_code == 200, r.text
    t1 = (await client.get(f"{API}/tickets/PA-1", headers=legal.headers)).json()
    assert t1["links"][0]["ticket"]["key"] == "PA-2"
    # Participants: luis is the assignee; with include_participants he sees it.
    assert (
        await client.get(f"{API}/tickets/PA-2", headers=board.member.headers)
    ).status_code == 404
    r = await client.patch(
        f"{API}/security-levels/{world['level']['id']}",
        headers=board.admin.headers,
        json={"include_participants": True},
    )
    assert r.status_code == 200
    assert (
        await client.get(f"{API}/tickets/PA-2", headers=board.member.headers)
    ).status_code == 200
    # Leaving the group takes it away at once.
    await client.delete(f"{API}/groups/equipo-legal/members/legal", headers=board.instance.headers)
    assert (await client.get(f"{API}/tickets/PA-2", headers=legal.headers)).status_code == 404


async def test_next_ticket_bulk_and_aliases_skip_it(
    client: AsyncClient, board: Team, world: dict
) -> None:
    r = await client.post(
        f"{API}/tickets/next", headers=board.member.headers, json={"project": "PA", "claim": False}
    )
    assert not leaks(r.text)
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={
            "query": "project = PA",
            "dry_run": True,
            "operations": [{"op": "add_tag", "tag": "x"}],
        },
    )
    assert r.status_code == 200 and not leaks(r.text)
    r = await client.post(
        f"{API}/tickets/bulk",
        headers=board.member.headers,
        json={"keys": ["PA-2"], "operations": [{"op": "add_tag", "tag": "x"}]},
    )
    assert r.json()["failed"] == 1 and "not found" in r.json()["results"][0]["error"]
    # A moved restricted ticket stays hidden under its old key.
    await make_project(client, board.instance, "PB")
    await client.post(
        f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": "Backend"}
    )
    r = await client.post(
        f"{API}/tickets/PA-2/move", headers=board.instance.headers, json={"target_project": "PB"}
    )
    assert r.status_code == 200, r.text
    assert (
        await client.get(f"{API}/tickets/PA-2", headers=board.member.headers)
    ).status_code == 404
    r = await client.get(f"{API}/tickets/PA-2", headers=board.instance.headers)
    assert r.status_code == 200


async def test_setting_the_level_needs_its_permission(client: AsyncClient, board: Team) -> None:
    await client.post(
        f"{API}/projects/PA/security-levels", headers=board.admin.headers, json={"name": "Privado"}
    )
    await new_ticket(client, board.member)
    r = await patch_ticket(client, board.member, "PA-1", security_level="Privado")
    assert r.status_code == 403 and "ticket.set_security" in r.json()["detail"]
    r = await patch_ticket(client, board.admin, "PA-1", security_level="Nope")
    assert r.status_code == 422 and "Privado" in r.json()["detail"]
    r = await patch_ticket(client, board.admin, "PA-1", security_level="Privado")
    assert r.status_code == 200
    history = (await client.get(f"{API}/tickets/PA-1/history", headers=board.admin.headers)).json()
    assert history["items"][0]["field"] == "security_level"
    levels = (
        await client.get(f"{API}/projects/PA/security-levels", headers=board.viewer.headers)
    ).json()["items"]
    r = await client.delete(f"{API}/security-levels/{levels[0]['id']}", headers=board.admin.headers)
    assert r.status_code == 409 and "Remove the level" in r.json()["detail"]
    r = await client.post(
        f"{API}/projects/PA/security-levels", headers=board.member.headers, json={"name": "X"}
    )
    assert r.status_code == 403


READ_TOOLS = {
    "search_tickets": {"query": "project = PA"},
    "my_tickets": {},
    "get_ticket": {"key": "PA-1"},
    "list_comments": {"key": "PA-1"},
    "get_history": {"key": "PA-1"},
    "list_attachments": {"key": "PA-1"},
    "list_worklogs": {"key": "PA-1"},
    "get_transitions": {"key": "PA-1"},
    "get_ticket_schema": {"project": "PA", "type": "task"},
    "list_projects": {},
    "get_project": {"project": "PA"},
    "whoami": {},
    "list_filters": {},
    "run_filter": {"name": "Todo"},
    "list_boards": {"project": "PA"},
    "get_board": {"board": "{main}"},
    "list_sprints": {"board": "{scrum}"},
    "get_sprint": {"sprint": "{sprint}"},
    "get_milestone_progress": {"project": "PA", "milestone": "V1"},
    "get_report": {"type": "time", "project": "PA"},
    "next_ticket": {"project": "PA"},
    "list_inbox": {"project": "PA"},
}


async def test_mcp_tools_do_not_leak(
    client: AsyncClient, board: Team, world: dict, mcp_for: McpFor
) -> None:
    async with mcp_for(board.agent) as mcp:
        tools = {t.name for t in (await mcp.list_tools()).tools}
        reading = {
            t
            for t in tools
            if t.split("_")[0] in ("get", "list", "search", "my", "run", "next", "read", "whoami")
        }
        assert reading <= set(READ_TOOLS) | {"read_attachment"}, sorted(reading - set(READ_TOOLS))
        for tool, args in READ_TOOLS.items():
            filled = {k: v.format(**world) if isinstance(v, str) else v for k, v in args.items()}
            result = await mcp.call_tool(tool, filled)
            assert not leaks(str(result.content)), (tool, str(result.content)[:300])
        result = await mcp.call_tool("get_ticket", {"key": "PA-2"})
        assert result.is_error and "not found" in error_text(result)
        result = await mcp.call_tool("read_attachment", {"attachment_id": world["attachment"]})
        assert result.is_error
        assert payload(await mcp.call_tool("search_tickets", {"query": "key = PA-2"}))["total"] == 0
