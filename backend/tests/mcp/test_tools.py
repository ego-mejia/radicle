"""Every tool: one success and at least one actionable error."""

import httpx2
import pytest
from httpx import AsyncClient

from tests.conftest import Team, new_ticket
from tests.mcp.conftest import McpFor, error_text, payload

TOOLS = {
    "whoami",
    "list_projects",
    "get_project",
    "search_tickets",
    "my_tickets",
    "get_ticket",
    "get_ticket_schema",
    "create_ticket",
    "update_ticket",
    "get_transitions",
    "transition_ticket",
    "change_ticket_type",
    "set_checklist_item",
    "add_comment",
    "list_comments",
    "link_tickets",
    "unlink_tickets",
    "add_collaborator",
    "remove_collaborator",
    "get_history",
    "upload_attachment",
    "list_attachments",
    "read_attachment",
    "log_work",
    "list_worklogs",
    "clone_ticket",
    "move_ticket",
    "bulk_update",
    "next_ticket",
    "rank_ticket",
    "list_filters",
    "run_filter",
    "save_filter",
    "list_boards",
    "get_board",
    "list_sprints",
    "get_sprint",
    "add_to_sprint",
    "remove_from_sprint",
    "start_sprint",
    "complete_sprint",
    "get_milestone_progress",
    "get_report",
    "list_inbox",
    "score_inbox_item",
    "approve_inbox_item",
    "discard_inbox_item",
    "mark_inbox_duplicate",
}


@pytest.fixture
async def seeded(client: AsyncClient, board: Team) -> Team:
    await new_ticket(client, board.member, title="Uno", description_md="- [ ] a\n- [ ] b @luis")
    await new_ticket(client, board.member, title="Dos", assignee="agent-backend")
    return board


async def test_tool_catalog(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        tools = (await mcp.list_tools()).tools
        assert {t.name for t in tools} == TOOLS
        assert all(t.description and len(t.description) > 20 for t in tools)
        update = next(t for t in tools if t.name == "update_ticket")
        assert "changes" in update.input_schema["properties"]


async def test_whoami_projects_and_project(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        assert payload(await mcp.call_tool("list_projects"))[0]["key"] == "PA"
        project = payload(await mcp.call_tool("get_project", {"project": "PA"}))
        assert project["areas"] == ["Legal", "Marketing", "Backend", "Frontend"]
        assert project["milestones"][0]["name"] == "V1"
        close = next(t for t in project["workflows"]["task"]["transitions"] if t["name"] == "Close")
        assert close == {
            "name": "Close",
            "from": "any not done",
            "to": "Done",
            "resolutions": ["wont_do", "duplicate"],
            "rules": [],
        }
        assert "Project ZZ not found" in error_text(
            await mcp.call_tool("get_project", {"project": "ZZ"})
        )


async def test_search_and_my_tickets(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        found = payload(await mcp.call_tool("search_tickets", {"query": "title ~ uno"}))
        assert found["total"] == 1 and found["items"][0]["key"] == "PA-1"
        assert set(found["items"][0]) >= {"key", "title", "status", "priority", "blocked"}
        warned = payload(await mcp.call_tool("search_tickets", {"query": "area = Nope"}))
        assert warned["warnings"] == ["Area 'Nope' does not exist; it matches nothing."]
        msg = error_text(await mcp.call_tool("search_tickets", {"query": "prioridad = high"}))
        assert "Did you mean 'priority'" in msg
        mine = payload(await mcp.call_tool("my_tickets", {"include_done": True}))
        assert [t["key"] for t in mine["items"]] == ["PA-2"]


async def test_get_ticket(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        t = payload(await mcp.call_tool("get_ticket", {"key": "PA-1", "comments": 0}))
        assert t["reporter"] == "luis" and t["status"] == "To Do" and t["version"] == 1
        assert "latest_comments" not in t and t["children"] == []
        assert "Ticket PA-99 not found" in error_text(
            await mcp.call_tool("get_ticket", {"key": "PA-99"})
        )


async def test_create_ticket(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        t = payload(
            await mcp.call_tool(
                "create_ticket",
                {
                    "project": "PA",
                    "type": "bug",
                    "title": "Falla",
                    "area": "Frontend",
                    "priority": "high",
                    "tags": ["ux"],
                    "parent": "PA-1",
                    "due_date": "2026-12-01",
                },
            )
        )
        assert t["key"] == "PA-3" and t["reporter"] == "agent-backend" and t["parent"] == "PA-1"
        msg = error_text(
            await mcp.call_tool(
                "create_ticket", {"project": "PA", "type": "task", "title": "x", "area": "Ventas"}
            )
        )
        assert "Valid areas: Legal, Marketing, Backend, Frontend" in msg


async def test_update_ticket(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        t = payload(
            await mcp.call_tool(
                "update_ticket",
                {
                    "key": "PA-1",
                    "changes": {"title": "Uno bis", "milestone": "V1", "description": "nuevo"},
                },
            )
        )
        assert t["title"] == "Uno bis" and t["milestone"] == "V1" and t["version"] == 2
        t = payload(
            await mcp.call_tool("update_ticket", {"key": "PA-1", "changes": {"milestone": None}})
        )
        assert t["milestone"] is None
        msg = error_text(
            await mcp.call_tool(
                "update_ticket", {"key": "PA-1", "changes": {"title": "x"}, "expected_version": 1}
            )
        )
        assert "Someone else changed PA-1" in msg
        assert "at least one field" in error_text(
            await mcp.call_tool("update_ticket", {"key": "PA-1", "changes": {}})
        )


async def test_transitions(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        options = payload(await mcp.call_tool("get_transitions", {"key": "PA-1"}))
        assert [o["to_status"] for o in options] == ["In Progress", "Done"]
        msg = error_text(
            await mcp.call_tool("transition_ticket", {"key": "PA-1", "to_status": "In Review"})
        )
        assert "Transition to 'In Review' not allowed from 'To Do'. Valid targets:" in msg
        assert "'Done' via 'Close' (resolutions: wont_do, duplicate)" in msg
        msg = error_text(
            await mcp.call_tool("transition_ticket", {"key": "PA-1", "to_status": "Done"})
        )
        assert "needs a resolution" in msg
        done = payload(
            await mcp.call_tool(
                "transition_ticket", {"key": "PA-1", "to_status": "Done", "resolution": "duplicate"}
            )
        )
        assert done["resolution"] == "duplicate" and done["warnings"] == []


async def test_change_type(seeded: Team, mcp_for: McpFor, client: AsyncClient) -> None:
    await new_ticket(
        client, seeded.member, type="draft", classification="idea", area=None, title="Idea"
    )
    async with mcp_for(seeded.agent) as mcp:
        assert "Area is required" in error_text(
            await mcp.call_tool("change_ticket_type", {"key": "PA-3", "type": "task"})
        )
        t = payload(
            await mcp.call_tool(
                "change_ticket_type", {"key": "PA-3", "type": "task", "area": "Legal"}
            )
        )
        assert t["type"] == "task" and t["status"] == "To Do"


async def test_checklist(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        t = payload(
            await mcp.call_tool("set_checklist_item", {"key": "PA-1", "index": 1, "checked": True})
        )
        assert [i["checked"] for i in t["checklist"]] == [False, True]
        assert "has 2 items" in error_text(
            await mcp.call_tool("set_checklist_item", {"key": "PA-1", "index": 5, "checked": True})
        )


async def test_comments(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        for body in ("primero", "segundo @luis"):
            payload(await mcp.call_tool("add_comment", {"key": "PA-1", "body": body}))
        page = payload(await mcp.call_tool("list_comments", {"key": "PA-1", "limit": 1}))
        assert [c["body"] for c in page["items"]] == ["segundo @luis"] and page["next_cursor"]
        t = payload(await mcp.call_tool("get_ticket", {"key": "PA-1"}))
        assert [c["body"] for c in t["latest_comments"]] == ["primero", "segundo @luis"]
        assert "cannot be empty" in error_text(
            await mcp.call_tool("add_comment", {"key": "PA-1", "body": "  "})
        )
        assert "not found" in error_text(await mcp.call_tool("list_comments", {"key": "PA-9"}))


async def test_links(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        links = payload(
            await mcp.call_tool(
                "link_tickets", {"source": "PA-1", "type": "relates_to", "target": "PA-2"}
            )
        )
        assert "already linked" in error_text(
            await mcp.call_tool(
                "link_tickets", {"source": "PA-2", "type": "relates_to", "target": "PA-1"}
            )
        )
        assert payload(await mcp.call_tool("unlink_tickets", {"link_id": links[0]["id"]})) == (
            "Link removed."
        )
        assert "not found" in error_text(
            await mcp.call_tool("unlink_tickets", {"link_id": links[0]["id"]})
        )


async def test_collaborators(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        t = payload(await mcp.call_tool("add_collaborator", {"key": "PA-1", "handle": "ana"}))
        assert t["collaborators"] == ["ana"]
        t = payload(await mcp.call_tool("remove_collaborator", {"key": "PA-1", "handle": "ana"}))
        assert t["collaborators"] == []
        assert "only active members" in error_text(
            await mcp.call_tool("add_collaborator", {"key": "PA-1", "handle": "vera"})
        )
        assert "not a collaborator" in error_text(
            await mcp.call_tool("remove_collaborator", {"key": "PA-1", "handle": "ana"})
        )


async def test_history(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        events = payload(await mcp.call_tool("get_history", {"key": "PA-1"}))
        assert events[0]["event"] == "created" and events[0]["actor"] == "luis"
        assert "not found" in error_text(await mcp.call_tool("get_history", {"key": "PB-1"}))


async def test_viewer_cannot_create(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.viewer) as mcp:
        msg = error_text(
            await mcp.call_tool(
                "create_ticket",
                {"project": "PA", "type": "draft", "classification": "idea", "title": "x"},
            )
        )
        assert "'ticket.create' permission is off for the viewer role" in msg


async def test_outsider_sees_nothing(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.outsider) as mcp:
        assert payload(await mcp.call_tool("list_projects")) == []
        assert "not found" in error_text(await mcp.call_tool("get_ticket", {"key": "PA-1"}))
        assert payload(await mcp.call_tool("search_tickets", {"query": ""}))["total"] == 0


async def test_resources(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.agent) as mcp:
        uris = {str(r.uri) for r in (await mcp.list_resources()).resources}
        assert "radicle://guide/rql" in uris
        guide = await mcp.read_resource("radicle://guide/rql")
        text = guide.contents[0].text
        assert "| `priority` |" in text and "currentUser()" in text
        schema = await mcp.read_resource("radicle://projects/PA/schema")
        assert '"areas"' in schema.contents[0].text


async def test_rejects_missing_revoked_and_bad_tokens(client: AsyncClient, seeded: Team) -> None:
    app = client._transport.app  # type: ignore[attr-defined]
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    headers = {"Accept": "application/json, text/event-stream"}
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url="http://t"
    ) as http:
        r = await http.post("/mcp", json=body, headers=headers)
        assert r.status_code == 401 and "Bearer rdc_" in r.json()["detail"]
        r = await http.post(
            "/mcp", json=body, headers={**headers, "Authorization": f"Bearer rdc_{'x' * 40}"}
        )
        assert r.status_code == 401 and "Unknown API token" in r.json()["detail"]

        r = await client.get("/api/v1/users/agent-backend/tokens", headers=seeded.instance.headers)
        token_id = r.json()["items"][0]["id"]
        await client.delete(
            f"/api/v1/users/agent-backend/tokens/{token_id}", headers=seeded.instance.headers
        )
        r = await http.post("/mcp", json=body, headers={**headers, **seeded.agent.headers})
        assert r.status_code == 401 and "revoked" in r.json()["detail"]


async def test_personal_token_also_works(seeded: Team, mcp_for: McpFor) -> None:
    async with mcp_for(seeded.member) as mcp:
        assert payload(await mcp.call_tool("whoami"))["kind"] == "human"
