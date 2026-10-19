import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, new_ticket, patch_ticket, run_jobs
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture, shared with MCP tests

API = "/api/v1"
ENV_FIELD = {
    "key": "environment",
    "name": "Environment",
    "field_type": "select",
    "options": [{"value": "prod"}, {"value": "staging"}],
    "applies_to_types": ["bug"],
}
BUG_CREATE = {
    "type": "bug",
    "operation": "create",
    "fields": [
        {"field": "title", "required": True},
        {"field": "area", "required": True},
        {"field": "cf.environment", "required": True},
        {"field": "priority"},
    ],
}
MESSAGE = "A bug in PA needs: Environment (cf.environment). Fill them in and try again."


@pytest.fixture
async def screened(client: AsyncClient, board: Team) -> Team:
    r = await client.post(f"{API}/projects/PA/detach", headers=board.instance.headers)
    assert r.status_code == 200
    r = await client.post(
        f"{API}/projects/PA/fields", headers=board.instance.headers, json=ENV_FIELD
    )
    assert r.status_code == 201
    r = await client.put(
        f"{API}/projects/PA/screens", headers=board.admin.headers, json={"screens": [BUG_CREATE]}
    )
    assert r.status_code == 200, r.text
    return board


async def test_acceptance_required_custom_field_same_in_api_and_mcp(
    client: AsyncClient, screened: Team, mcp_for: McpFor
) -> None:
    body = {"type": "bug", "title": "Falla el login", "area": "Frontend"}
    r = await client.post(f"{API}/projects/PA/tickets", headers=screened.member.headers, json=body)
    assert r.status_code == 422
    assert r.json()["detail"] == MESSAGE
    assert r.json()["errors"] == [{"field": "cf.environment", "message": "required"}]

    async with mcp_for(screened.agent) as mcp:
        result = await mcp.call_tool("create_ticket", {"project": "PA", **body})
        assert error_text(result).endswith(MESSAGE)
        schema = payload(await mcp.call_tool("get_ticket_schema", {"project": "PA", "type": "bug"}))
        env = next(f for f in schema["fields"] if f["field"] == "cf.environment")
        assert env == {
            "field": "cf.environment",
            "kind": "select",
            "required": True,
            "options": ["prod", "staging"],
            "label": "Environment",
        }

    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=screened.member.headers,
        json={**body, "custom_fields": {"environment": "prod"}},
    )
    assert r.status_code == 201
    # Tasks have no screen: the stage 1 defaults still apply.
    r = await client.post(
        f"{API}/projects/PA/tickets",
        headers=screened.member.headers,
        json={"type": "task", "title": "x"},
    )
    assert r.status_code == 422 and "Area is required" in r.json()["detail"]


async def test_schema_endpoint(client: AsyncClient, screened: Team) -> None:
    r = await client.get(
        f"{API}/projects/PA/schema", headers=screened.viewer.headers, params={"type": "bug"}
    )
    schema = r.json()
    assert schema["from_screen"] is True
    assert [(f["field"], f["required"]) for f in schema["fields"]] == [
        ("title", True),
        ("area", True),
        ("cf.environment", True),
        ("priority", False),
    ]
    area = schema["fields"][1]
    assert area["kind"] == "area" and area["options"] == [
        "Legal",
        "Marketing",
        "Backend",
        "Frontend",
    ]
    assert schema["fields"][3]["options"] == ["highest", "high", "medium", "low", "lowest"]

    r = await client.get(
        f"{API}/projects/PA/schema",
        headers=screened.viewer.headers,
        params={"type": "draft", "classification": "idea"},
    )
    draft = r.json()
    assert draft["from_screen"] is False
    required = {f["field"]: f["required"] for f in draft["fields"]}
    assert required["title"] is True and required["area"] is False
    assert "cf.environment" not in required  # only for bugs

    r = await client.get(
        f"{API}/projects/PA/schema",
        headers=screened.viewer.headers,
        params={"type": "bug", "operation": "edit"},
    )
    edit = r.json()
    assert edit["from_screen"] is False
    assert {f["field"]: f["required"] for f in edit["fields"]}["area"] is False
    assert "cf.environment" in [f["field"] for f in edit["fields"]]
    assert "luis" in next(f for f in edit["fields"] if f["field"] == "assignee")["options"]

    r = await client.get(
        f"{API}/projects/PA/schema",
        headers=screened.viewer.headers,
        params={"type": "bug", "operation": "transition"},
    )
    assert r.status_code == 422
    r = await client.get(
        f"{API}/projects/PA/schema",
        headers=screened.viewer.headers,
        params={"type": "bug", "operation": "transition", "transition": "Nope"},
    )
    assert r.status_code == 422 and "Transitions:" in r.json()["detail"]
    r = await client.get(
        f"{API}/projects/PA/schema",
        headers=screened.outsider.headers,
        params={"type": "bug"},
    )
    assert r.status_code == 404


async def test_edit_screen_makes_other_fields_read_only(
    client: AsyncClient, screened: Team
) -> None:
    edit = {
        "type": "task",
        "operation": "edit",
        "fields": [{"field": "title", "required": True}, {"field": "milestone", "required": True}],
    }
    r = await client.put(
        f"{API}/projects/PA/screens",
        headers=screened.admin.headers,
        json={"screens": [BUG_CREATE, edit]},
    )
    assert r.status_code == 200
    await new_ticket(client, screened.member, milestone="V1")
    r = await patch_ticket(client, screened.member, "PA-1", priority="high")
    assert r.status_code == 422
    assert r.json()["detail"] == (
        "These fields are read-only for task tickets in PA: priority. Editable: milestone, title."
    )
    r = await patch_ticket(client, screened.member, "PA-1", milestone=None)
    assert r.status_code == 422 and "needs: Milestone" in r.json()["detail"]
    r = await patch_ticket(client, screened.member, "PA-1", title="Nuevo título")
    assert r.status_code == 200
    r = await patch_ticket(client, screened.admin, "PA-1", priority="high")
    assert r.status_code == 200  # admins can edit anything


async def test_transition_screen(client: AsyncClient, screened: Team) -> None:
    complete = {
        "type": "bug",
        "operation": "transition",
        "transition": "Send to QA",
        "fields": [{"field": "cf.environment", "required": True}, {"field": "estimate_hours"}],
    }
    r = await client.put(
        f"{API}/projects/PA/screens", headers=screened.admin.headers, json={"screens": [complete]}
    )
    assert r.status_code == 200
    assert r.json()["items"][0]["transition"] == "send_to_qa"
    await new_ticket(client, screened.member, type="bug")
    move = f"{API}/tickets/PA-1/transitions"
    await client.post(move, headers=screened.member.headers, json={"to_status": "In Progress"})
    options = (await client.get(move, headers=screened.member.headers)).json()
    assert {o["name"]: o["has_screen"] for o in options}["Send to QA"] is True

    r = await client.post(move, headers=screened.member.headers, json={"to_status": "QA Verified"})
    assert r.status_code == 422 and r.json()["detail"] == MESSAGE
    r = await client.post(
        move,
        headers=screened.member.headers,
        json={"to_status": "QA Verified", "fields": {"priority": "high"}},
    )
    assert r.status_code == 422 and "does not take these fields: priority" in r.json()["detail"]
    r = await client.post(
        move,
        headers=screened.member.headers,
        json={
            "to_status": "QA Verified",
            "fields": {"cf.environment": "staging", "estimate_hours": 2},
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["custom_fields"] == {"environment": "staging"}
    assert r.json()["estimate_hours"] == 2


async def test_put_screens_validation_and_linked_projects(
    client: AsyncClient, screened: Team
) -> None:
    url = f"{API}/projects/PA/screens"
    cases = [
        (
            {"type": "bug", "operation": "create", "fields": [{"field": "titulo"}]},
            "Unknown screen field",
        ),
        (
            {
                "type": "bug",
                "operation": "create",
                "fields": [{"field": "area"}, {"field": "area"}],
            },
            "repeated",
        ),
        ({"type": "bug", "operation": "transition", "fields": []}, "need `transition`"),
        (
            {"type": "bug", "operation": "edit", "transition": "Start", "fields": []},
            "Only transition",
        ),
    ]
    for screen, message in cases:
        r = await client.put(url, headers=screened.admin.headers, json={"screens": [screen]})
        assert r.status_code == 422, screen
        assert message in r.json()["detail"]
    r = await client.put(
        url, headers=screened.admin.headers, json={"screens": [BUG_CREATE, BUG_CREATE]}
    )
    assert r.status_code == 422 and "Two screens" in r.json()["detail"]
    r = await client.put(url, headers=screened.member.headers, json={"screens": []})
    assert r.status_code == 403
    r = await client.put(url, headers=screened.admin.headers, json={"screens": []})
    assert r.json()["items"] == []


async def test_screens_travel_with_templates(
    client: AsyncClient, db: AsyncSession, screened: Team
) -> None:
    r = await client.post(
        f"{API}/projects/PA/save-as-template", headers=screened.admin.headers, json={"name": "QA"}
    )
    template = r.json()
    assert template["config"]["screens"] == [
        {
            "type": "bug",
            "operation": "create",
            "transition": None,
            "fields": [
                {"field": "title", "required": True},
                {"field": "area", "required": True},
                {"field": "cf.environment", "required": True},
                {"field": "priority", "required": False},
            ],
        }
    ]
    r = await client.post(
        f"{API}/projects",
        headers=screened.instance.headers,
        json={"key": "PB", "name": "B", "template_id": template["id"]},
    )
    r = await client.get(f"{API}/projects/PB/screens", headers=screened.instance.headers)
    assert [s["operation"] for s in r.json()["items"]] == ["create"]
    r = await client.put(
        f"{API}/projects/PB/screens", headers=screened.instance.headers, json={"screens": []}
    )
    assert r.status_code == 409

    config = template["config"]
    config["screens"].append(
        {
            "type": "bug",
            "operation": "transition",
            "transition": "complete",
            "fields": [{"field": "cf.environment", "required": True}],
        }
    )
    r = await client.patch(
        f"{API}/templates/{template['id']}",
        headers=screened.instance.headers,
        json={"config": config},
    )
    assert r.status_code == 200, r.text
    await run_jobs(db)
    r = await client.get(f"{API}/projects/PB/screens", headers=screened.instance.headers)
    assert [(s["operation"], s["transition"]) for s in r.json()["items"]] == [
        ("create", None),
        ("transition", "complete"),
    ]
    config["screens"][-1]["transition"] = "nope"
    r = await client.patch(
        f"{API}/templates/{template['id']}",
        headers=screened.instance.headers,
        json={"config": config},
    )
    assert r.status_code == 422 and "unknown transition 'nope'" in r.json()["detail"]
