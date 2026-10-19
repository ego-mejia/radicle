from httpx import AsyncClient

from tests.conftest import Team
from tests.mcp.conftest import McpFor, error_text, payload


async def test_agent_fills_and_filters_custom_fields(
    client: AsyncClient, board: Team, mcp_for: McpFor
) -> None:
    r = await client.post(
        "/api/v1/projects/PA/fields",
        headers=board.admin.headers,
        json={
            "key": "environment",
            "name": "Environment",
            "field_type": "select",
            "options": [{"value": "prod"}, {"value": "dev"}],
            "applies_to_types": ["bug"],
        },
    )
    assert r.status_code == 201
    async with mcp_for(board.agent) as mcp:
        project = payload(await mcp.call_tool("get_project", {"project": "PA"}))
        assert project["custom_fields"] == [
            {
                "key": "environment",
                "name": "Environment",
                "type": "select",
                "options": ["prod", "dev"],
                "applies_to_types": ["bug"],
                "applies_to_areas": None,
            }
        ]
        bad = await mcp.call_tool(
            "create_ticket",
            {
                "project": "PA",
                "type": "bug",
                "title": "Falla",
                "area": "Backend",
                "custom_fields": {"environment": "qa"},
            },
        )
        assert "Options: prod, dev" in error_text(bad)
        created = payload(
            await mcp.call_tool(
                "create_ticket",
                {
                    "project": "PA",
                    "type": "bug",
                    "title": "Falla",
                    "area": "Backend",
                    "custom_fields": {"environment": "dev"},
                },
            )
        )
        assert created["custom_fields"] == {"environment": "dev"}
        updated = payload(
            await mcp.call_tool(
                "update_ticket",
                {"key": created["key"], "changes": {"custom_fields": {"environment": "prod"}}},
            )
        )
        assert updated["custom_fields"] == {"environment": "prod"}
        found = payload(await mcp.call_tool("search_tickets", {"query": "cf.environment = prod"}))
        assert [t["key"] for t in found["items"]] == [created["key"]]
