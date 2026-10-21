from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import DailyStatusCount, Sprint
from radicle.docket.services import periods
from tests.conftest import Team, new_ticket, patch_ticket
from tests.mcp.conftest import McpFor, error_text, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"
TODAY = date.today()


@pytest.fixture
async def scrum(client: AsyncClient, board: Team) -> dict:
    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=board.admin.headers,
        json={"name": "Scrum PA", "kind": "scrum"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def new_sprint(client: AsyncClient, team: Team, board: dict, **body: object) -> dict:
    r = await client.post(
        f"{API}/boards/{board['id']}/sprints", headers=team.admin.headers, json=body
    )
    assert r.status_code == 201, r.text
    return r.json()


async def add(client: AsyncClient, actor, sprint: dict, *keys: str):  # type: ignore[no-untyped-def]
    return await client.post(
        f"{API}/sprints/{sprint['id']}/tickets", headers=actor.headers, json={"keys": list(keys)}
    )


async def start(client: AsyncClient, team: Team, sprint: dict, days: int = 14, **body: object):  # type: ignore[no-untyped-def]
    end = TODAY + timedelta(days=days - 1)
    return await client.post(
        f"{API}/sprints/{sprint['id']}/start",
        headers=team.admin.headers,
        json={"start_date": TODAY.isoformat(), "end_date": end.isoformat(), **body},
    )


async def get_sprint(client: AsyncClient, team: Team, sprint: dict) -> dict:
    r = await client.get(f"{API}/sprints/{sprint['id']}", headers=team.viewer.headers)
    assert r.status_code == 200, r.text
    return r.json()


async def finish(client: AsyncClient, team: Team, key: str) -> None:
    for status in ("In Progress", "In Review", "Done"):
        body: dict[str, object] = {"to_status": status}
        if status == "Done":
            body["resolution"] = "done"
        r = await client.post(
            f"{API}/tickets/{key}/transitions", headers=team.member.headers, json=body
        )
        assert r.status_code == 200, r.text


async def search(client: AsyncClient, team: Team, q: str) -> list[str]:
    r = await client.get(f"{API}/tickets", headers=team.viewer.headers, params={"q": q})
    assert r.status_code == 200, r.text
    return [t["key"] for t in r.json()["items"]]


async def test_acceptance_full_sprint(client: AsyncClient, board: Team, scrum: dict) -> None:
    """Plan from the backlog with capacity, start, add mid-sprint, close to #backlog."""
    for i, hours in enumerate((8, 5, 3)):
        await new_ticket(
            client, board.member, title=f"t{i}", estimate_hours=hours, tags=["backlog"]
        )
    await new_ticket(client, board.member, title="sin estimar")
    sprint = await new_sprint(client, board, scrum, goal="Pagos", capacity_hours=12)
    assert sprint["name"] == "Sprint 1" and sprint["state"] == "future"

    r = await client.get(f"{API}/boards/{scrum['id']}/backlog", headers=board.viewer.headers)
    assert [t["key"] for t in r.json()["items"]] == ["PA-1", "PA-2", "PA-3", "PA-4"]

    r = await add(client, board.member, sprint, "PA-1", "PA-2", "PA-4")
    assert r.json()["keys"] == ["PA-1", "PA-2", "PA-4"]
    planned = await get_sprint(client, board, sprint)
    assert planned["estimate_hours"] == 13 and planned["over_capacity"] is True
    assert planned["unestimated_count"] == 1
    # Joining a sprint removes #backlog, and the backlog no longer lists them.
    assert "backlog" not in planned["tickets"][0]["tags"]
    r = await client.get(f"{API}/boards/{scrum['id']}/backlog", headers=board.viewer.headers)
    assert [t["key"] for t in r.json()["items"]] == ["PA-3"]

    r = await start(client, board, sprint)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "active"
    # The scrum board shows the active sprint.
    data = (
        await client.get(f"{API}/boards/{scrum['id']}/data", headers=board.viewer.headers)
    ).json()
    assert data["sprint"]["name"] == "Sprint 1"
    assert sorted(t["key"] for c in data["columns"] for t in c["tickets"]) == [
        "PA-1",
        "PA-2",
        "PA-4",
    ]

    # Adding mid-sprint is a scope change.
    assert (await add(client, board.member, sprint, "PA-3")).status_code == 200
    await finish(client, board, "PA-1")
    report = (
        await client.get(f"{API}/sprints/{sprint['id']}/report", headers=board.viewer.headers)
    ).json()
    assert report["committed_hours"] == 13
    assert [i["key"] for i in report["added_after_start"]] == ["PA-3"]
    assert [i["key"] for i in report["completed"]] == ["PA-1"]

    r = await client.post(
        f"{API}/sprints/{sprint['id']}/complete", headers=board.admin.headers, json={}
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["sprint"]["state"] == "closed" and out["moved_to"] is None
    assert sorted(out["unfinished"]) == ["PA-2", "PA-3", "PA-4"]
    assert await search(client, board, "#backlog ORDER BY key") == ["PA-2", "PA-3", "PA-4"]
    assert await search(client, board, "sprint IS EMPTY ORDER BY key") == [
        "PA-1",
        "PA-2",
        "PA-3",
        "PA-4",
    ]
    assert await search(client, board, 'sprint = "Sprint 1"') == ["PA-1"]

    # The saved report does not change afterwards; goal_met is marked by hand.
    await finish(client, board, "PA-2")
    r = await client.patch(
        f"{API}/sprints/{sprint['id']}", headers=board.admin.headers, json={"goal_met": True}
    )
    assert r.status_code == 200, r.text
    report = (
        await client.get(f"{API}/sprints/{sprint['id']}/report", headers=board.viewer.headers)
    ).json()
    assert [i["key"] for i in report["completed"]] == ["PA-1"]
    assert sorted(i["key"] for i in report["not_completed"]) == ["PA-2", "PA-3", "PA-4"]
    assert report["goal_met"] is True and report["completed_hours"] == 8


async def test_close_moves_unfinished_to_next_sprint(
    client: AsyncClient, board: Team, scrum: dict
) -> None:
    await new_ticket(client, board.member)
    one = await new_sprint(client, board, scrum)
    two = await new_sprint(client, board, scrum)
    await add(client, board.member, one, "PA-1")
    assert (await start(client, board, one)).status_code == 200
    r = await client.post(
        f"{API}/sprints/{one['id']}/complete",
        headers=board.admin.headers,
        json={"move_unfinished_to": two["id"]},
    )
    assert r.json()["moved_to"]["name"] == "Sprint 2"
    assert [t["key"] for t in (await get_sprint(client, board, two))["tickets"]] == ["PA-1"]
    assert await search(client, board, "sprint = future") == ["PA-1"]
    assert await search(client, board, "#backlog") == []

    r = await client.post(
        f"{API}/sprints/{one['id']}/complete",
        headers=board.admin.headers,
        json={"move_unfinished_to": "nope"},
    )
    assert r.status_code == 409  # closed already


async def test_state_machine_and_rules(client: AsyncClient, board: Team, scrum: dict) -> None:
    one = await new_sprint(client, board, scrum)
    two = await new_sprint(client, board, scrum)
    # Dates are required, and 1 to 28 days.
    r = await client.post(f"{API}/sprints/{one['id']}/start", headers=board.admin.headers, json={})
    assert r.status_code == 422 and "start and an end date" in r.json()["detail"]
    r = await start(client, board, one, days=29)
    assert r.status_code == 422 and "between 1 and 28 days" in r.json()["detail"]
    assert (await start(client, board, one)).status_code == 200
    # One active per board.
    r = await start(client, board, two)
    assert r.status_code == 409 and "still active" in r.json()["detail"]
    # Active: only goal, end date, capacity.
    r = await client.patch(
        f"{API}/sprints/{one['id']}", headers=board.admin.headers, json={"name": "Otro"}
    )
    assert r.status_code == 409 and "change name" in r.json()["detail"]
    r = await client.patch(
        f"{API}/sprints/{one['id']}", headers=board.admin.headers, json={"goal": "Meta"}
    )
    assert r.json()["goal"] == "Meta"
    # Only future sprints can be deleted.
    r = await client.delete(f"{API}/sprints/{one['id']}", headers=board.admin.headers)
    assert r.status_code == 409
    assert (
        await client.delete(f"{API}/sprints/{two['id']}", headers=board.admin.headers)
    ).status_code == 204
    # Closed: read only.
    await client.post(f"{API}/sprints/{one['id']}/complete", headers=board.admin.headers, json={})
    await new_ticket(client, board.member)
    assert (await add(client, board.member, one, "PA-1")).status_code == 409
    listed = await client.get(f"{API}/boards/{scrum['id']}/sprints", headers=board.viewer.headers)
    assert [s["state"] for s in listed.json()["items"]] == ["closed"]


async def test_ticket_in_one_open_sprint(client: AsyncClient, board: Team, scrum: dict) -> None:
    await new_ticket(client, board.member)
    one = await new_sprint(client, board, scrum)
    two = await new_sprint(client, board, scrum)
    await add(client, board.member, one, "PA-1")
    await add(client, board.member, two, "PA-1")
    assert (await get_sprint(client, board, one))["ticket_count"] == 0
    assert (await get_sprint(client, board, two))["ticket_count"] == 1
    r = await client.request(
        "DELETE",
        f"{API}/sprints/{one['id']}/tickets",
        headers=board.member.headers,
        json={"keys": ["PA-1"]},
    )
    assert r.status_code == 422 and "not in 'Sprint 1'" in r.json()["detail"]
    r = await client.request(
        "DELETE",
        f"{API}/sprints/{two['id']}/tickets",
        headers=board.member.headers,
        json={"keys": ["PA-1"]},
    )
    assert r.json()["keys"] == ["PA-1"]
    history = await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)
    kinds = [e["event_type"] for e in history.json()["items"]]
    assert kinds.count("sprint_added") == 2 and kinds.count("sprint_removed") == 2


async def test_permissions_and_kanban(client: AsyncClient, board: Team, scrum: dict) -> None:
    main = (await client.get(f"{API}/projects/PA/boards", headers=board.viewer.headers)).json()[
        "items"
    ][0]
    r = await client.post(
        f"{API}/boards/{main['id']}/sprints", headers=board.admin.headers, json={}
    )
    assert r.status_code == 422 and "Kanban" in r.json()["detail"]
    r = await client.post(
        f"{API}/boards/{scrum['id']}/sprints", headers=board.member.headers, json={}
    )
    assert r.status_code == 403
    sprint = await new_sprint(client, board, scrum)
    await new_ticket(client, board.member)
    assert (await add(client, board.viewer, sprint, "PA-1")).status_code == 403
    r = await client.get(f"{API}/sprints/{sprint['id']}", headers=board.outsider.headers)
    assert r.status_code == 404
    r = await client.post(
        f"{API}/sprints/{sprint['id']}/start", headers=board.member.headers, json={}
    )
    assert r.status_code == 403


async def test_rql_start_field(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    r = await patch_ticket(client, board.member, "PA-1", start_date="2026-11-02")
    assert r.status_code == 200, r.text
    assert await search(client, board, "start >= 2026-11-01") == ["PA-1"]
    assert await search(client, board, "start IS EMPTY") == ["PA-2"]
    assert await search(client, board, "ORDER BY start ASC") == ["PA-1", "PA-2"]
    r = await client.get(
        f"{API}/tickets", headers=board.viewer.headers, params={"q": 'sprint = "Nada"'}
    )
    assert r.json()["warnings"][0]["message"] == "Sprint 'Nada' does not exist; it matches nothing."


async def test_snapshot_counts_by_sprint(
    client: AsyncClient, db: AsyncSession, board: Team, scrum: dict
) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    sprint = await new_sprint(client, board, scrum)
    await add(client, board.member, sprint, "PA-1")
    sprint_id = await db.scalar(select(Sprint.id))
    await periods.snapshot(db, periods.today())
    rows = (await db.scalars(select(DailyStatusCount))).all()
    by_sprint = {r.sprint_key: r.ticket_count for r in rows}
    assert by_sprint[sprint_id] == 1 and by_sprint[periods.ZERO] == 1


async def test_mcp_sprints(client: AsyncClient, board: Team, scrum: dict, mcp_for: McpFor) -> None:
    await new_ticket(client, board.member, estimate_hours=4)
    sprint = await new_sprint(client, board, scrum, goal="Meta")
    async with mcp_for(board.agent) as mcp:
        listed = payload(await mcp.call_tool("list_sprints", {"board": scrum["id"]}))
        assert listed[0]["name"] == "Sprint 1"
        added = payload(
            await mcp.call_tool("add_to_sprint", {"sprint": sprint["id"], "keys": ["PA-1"]})
        )
        assert added == {"added": ["PA-1"]}
        detail = payload(await mcp.call_tool("get_sprint", {"sprint": sprint["id"]}))
        assert detail["goal"] == "Meta" and detail["estimate_hours"] == 4
        assert detail["ticket_list"][0]["key"] == "PA-1"
        # Agents are members, not admins.
        result = await mcp.call_tool("start_sprint", {"sprint": sprint["id"]})
        assert result.is_error and "admin" in error_text(result).lower()
        removed = payload(
            await mcp.call_tool("remove_from_sprint", {"sprint": sprint["id"], "keys": ["PA-1"]})
        )
        assert removed == {"removed": ["PA-1"]}
    async with mcp_for(board.admin) as mcp:
        started = payload(
            await mcp.call_tool(
                "start_sprint",
                {
                    "sprint": sprint["id"],
                    "start_date": TODAY.isoformat(),
                    "end_date": (TODAY + timedelta(days=6)).isoformat(),
                },
            )
        )
        assert started["state"] == "active"
        closed = payload(await mcp.call_tool("complete_sprint", {"sprint": sprint["id"]}))
        assert closed["sprint"]["state"] == "closed" and closed["moved_to"] == "backlog"
