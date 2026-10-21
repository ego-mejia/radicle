"""Areas and milestones over MCP: create, edit, archive, close, and their errors."""

from tests.conftest import Team
from tests.mcp.conftest import McpFor, error_text, payload


async def test_create_and_update_area(board: Team, mcp_for: McpFor) -> None:
    async with mcp_for(board.admin) as mcp:
        area = payload(
            await mcp.call_tool(
                "create_area",
                {"project": "PA", "name": "Design ops", "color": "#4d7c0f", "icon": "rocket"},
            )
        )
        assert area == {
            "name": "Design ops",
            "color": "#4D7C0F",
            "icon": "rocket",
            "position": 4,
            "archived": False,
        }
        renamed = payload(
            await mcp.call_tool(
                "update_area",
                {
                    "project": "PA",
                    "area": "Design ops",
                    "changes": {"name": "Design", "icon": None},
                },
            )
        )
        assert renamed["name"] == "Design" and renamed["icon"] is None
        assert renamed["color"] == "#4D7C0F"
        archived = payload(
            await mcp.call_tool(
                "update_area", {"project": "PA", "area": "Design", "changes": {"archived": True}}
            )
        )
        assert archived["archived"] is True
        project = payload(await mcp.call_tool("get_project", {"project": "PA"}))
        assert "Design" not in project["areas"]


async def test_area_errors(board: Team, mcp_for: McpFor) -> None:
    async with mcp_for(board.admin) as mcp:
        dup = error_text(await mcp.call_tool("create_area", {"project": "PA", "name": "legal"}))
        assert "already exists" in dup
        color = error_text(
            await mcp.call_tool("create_area", {"project": "PA", "name": "Ops", "color": "red"})
        )
        assert "#4D7C0F" in color
        missing = error_text(
            await mcp.call_tool(
                "update_area", {"project": "PA", "area": "Nope", "changes": {"name": "X"}}
            )
        )
        assert "Nope" in missing
        empty = error_text(
            await mcp.call_tool("update_area", {"project": "PA", "area": "Legal", "changes": {}})
        )
        assert "at least one field" in empty


async def test_create_and_update_milestone(board: Team, mcp_for: McpFor) -> None:
    async with mcp_for(board.admin) as mcp:
        milestone = payload(
            await mcp.call_tool(
                "create_milestone",
                {
                    "project": "PA",
                    "name": "V2",
                    "description": "Second release",
                    "target_date": "2027-03-01",
                },
            )
        )
        assert milestone["name"] == "V2" and milestone["status"] == "open"
        assert milestone["target_date"] == "2027-03-01"
        assert milestone["description"] == "Second release"
        cleared = payload(
            await mcp.call_tool(
                "update_milestone",
                {
                    "project": "PA",
                    "milestone": "V2",
                    "changes": {"target_date": None, "description": "Later"},
                },
            )
        )
        assert cleared["target_date"] is None and cleared["description"] == "Later"
        closed = payload(
            await mcp.call_tool(
                "update_milestone",
                {"project": "PA", "milestone": "V2", "changes": {"status": "closed"}},
            )
        )
        assert closed["status"] == "closed"
        project = payload(await mcp.call_tool("get_project", {"project": "PA"}))
        assert "V2" not in project["milestones"]


async def test_milestone_errors(board: Team, mcp_for: McpFor) -> None:
    async with mcp_for(board.admin) as mcp:
        dup = error_text(await mcp.call_tool("create_milestone", {"project": "PA", "name": "v1"}))
        assert "already exists" in dup
        missing = error_text(
            await mcp.call_tool(
                "update_milestone",
                {"project": "PA", "milestone": "V9", "changes": {"status": "closed"}},
            )
        )
        assert "V9" in missing


async def test_members_cannot_manage_areas_or_milestones(board: Team, mcp_for: McpFor) -> None:
    async with mcp_for(board.agent) as mcp:
        area = error_text(await mcp.call_tool("create_area", {"project": "PA", "name": "Ops"}))
        milestone = error_text(
            await mcp.call_tool("create_milestone", {"project": "PA", "name": "V2"})
        )
        for text in (area, milestone):
            assert "admin" in text.lower() or "permission" in text.lower()
