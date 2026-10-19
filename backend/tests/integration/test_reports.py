"""Reports against a history with known dates: the expected numbers are worked out by hand."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.conftest import Clock, Team, new_ticket, patch_ticket
from tests.mcp.conftest import McpFor, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


def at(day: int, hour: int = 9) -> datetime:
    """September 2026; the 7th is a Monday."""
    return datetime(2026, 9, day, hour, tzinfo=UTC)


async def move(client: AsyncClient, team: Team, key: str, status: str) -> None:
    body: dict[str, object] = {"to_status": status}
    if status == "Done":
        body["resolution"] = "done"
    r = await client.post(
        f"{API}/tickets/{key}/transitions", headers=team.member.headers, json=body
    )
    assert r.status_code == 200, r.text


async def report(client: AsyncClient, team: Team, kind: str, **params: object) -> dict:
    r = await client.get(f"{API}/reports/{kind}", headers=team.viewer.headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
async def history(client: AsyncClient, board: Team, clock: Clock) -> dict:
    """Sprint 1 (Sep 7-18, 16 h committed) on a Scrum board:
    - Mon 7: PA-1 8 h, PA-2 5 h, PA-3 3 h in the sprint; PA-4 4 h (Frontend) outside.
    - Tue 8: 2 h logged on PA-1 (remaining 8 -> 6).
    - Wed 9: PA-2 goes to done between 10:00 and 12:00.
    - Thu 10: PA-4 joins the sprint (scope change).
    - Fri 11: PA-1 remaining set by hand to 3.
    - Mon 14 - Tue 15: PA-3 in progress at 9:00 Monday, done 9:00 Tuesday; 4 h logged.
    """
    clock.set(at(7))
    for title, hours, area in (
        ("Pagos", 8, "Backend"),
        ("Recibos", 5, "Backend"),
        ("Webhooks", 3, "Backend"),
        ("Login", 4, "Frontend"),
    ):
        await new_ticket(
            client, board.member, title=title, estimate_hours=hours, area=area, milestone="V1"
        )
    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=board.admin.headers,
        json={"name": "Scrum", "kind": "scrum"},
    )
    scrum = r.json()
    r = await client.post(
        f"{API}/boards/{scrum['id']}/sprints", headers=board.admin.headers, json={}
    )
    sprint = r.json()
    r = await client.post(
        f"{API}/sprints/{sprint['id']}/tickets",
        headers=board.member.headers,
        json={"keys": ["PA-1", "PA-2", "PA-3"]},
    )
    assert r.status_code == 200, r.text
    clock.set(at(7, 10))
    r = await client.post(
        f"{API}/sprints/{sprint['id']}/start",
        headers=board.admin.headers,
        json={"start_date": "2026-09-07", "end_date": "2026-09-18"},
    )
    assert r.status_code == 200, r.text

    clock.set(at(8, 10))
    r = await client.post(
        f"{API}/tickets/PA-1/worklogs", headers=board.member.headers, json={"minutes": 120}
    )
    assert r.status_code == 201, r.text
    for hour, status in ((10, "In Progress"), (11, "In Review"), (12, "Done")):
        clock.set(at(9, hour))
        await move(client, board, "PA-2", status)
    clock.set(at(10))
    await client.post(
        f"{API}/sprints/{sprint['id']}/tickets",
        headers=board.member.headers,
        json={"keys": ["PA-4"]},
    )
    clock.set(at(11))
    assert (await patch_ticket(client, board.member, "PA-1", remaining_hours=3)).status_code == 200
    clock.set(at(14))
    await move(client, board, "PA-3", "In Progress")
    clock.set(at(14, 15))
    await move(client, board, "PA-3", "In Review")
    r = await client.post(
        f"{API}/tickets/PA-3/worklogs", headers=board.member.headers, json={"minutes": 240}
    )
    clock.set(at(15))
    await move(client, board, "PA-3", "Done")
    return {"board": scrum, "sprint": sprint}


async def test_burndown_and_burnup(
    client: AsyncClient, board: Team, clock: Clock, history: dict
) -> None:
    clock.set(at(11, 15))
    data = await report(client, board, "burndown", sprint=history["sprint"]["id"])
    rows = data["rows"]
    assert [r["date"] for r in rows][:5] == [
        "2026-09-07",
        "2026-09-08",
        "2026-09-09",
        "2026-09-10",
        "2026-09-11",
    ]
    assert len(rows) == 10  # working days only
    assert [r["ideal_hours"] for r in rows][::3] == [16.0, 10.67, 5.33, 0.0]
    assert [r["remaining_hours"] for r in rows[:6]] == [16, 14, 9, 13, 10, None]
    assert [r["scope_change"] for r in rows[:5]] == [False, False, False, True, False]
    assert data["summary"]["committed_hours"] == 16

    up = await report(client, board, "burnup", sprint=history["sprint"]["id"])
    assert [(r["scope_hours"], r["completed_hours"]) for r in up["rows"]] == [
        (16, 0),
        (16, 0),
        (16, 5),
        (20, 5),
        (20, 5),
    ]


async def test_sprint_report_velocity_and_csv(
    client: AsyncClient, board: Team, clock: Clock, history: dict
) -> None:
    sprint = history["sprint"]
    clock.set(at(18, 17))
    r = await client.post(
        f"{API}/sprints/{sprint['id']}/complete", headers=board.admin.headers, json={}
    )
    assert r.status_code == 200, r.text
    data = await report(client, board, "sprint", sprint=sprint["id"])
    assert data["summary"]["counts"] == {
        "completed": 2,
        "not_completed": 2,
        "added_after_start": 1,
        "removed": 0,
    }
    assert data["summary"]["committed_hours"] == 16 and data["summary"]["completed_hours"] == 8
    outcomes = {(r["outcome"], r["key"]) for r in data["rows"]}
    assert ("added_after_start", "PA-4") in outcomes and ("completed", "PA-3") in outcomes

    velocity = await report(client, board, "velocity", board=history["board"]["id"])
    assert velocity["rows"] == [{"sprint": "Sprint 1", "committed_hours": 16, "completed_hours": 8}]
    assert velocity["summary"]["average_completed_hours"] == 8

    r = await client.get(
        f"{API}/reports/velocity.csv",
        headers=board.viewer.headers,
        params={"board": history["board"]["id"]},
    )
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines() == ["sprint,committed_hours,completed_hours", "Sprint 1,16.0,8.0"]

    # The burndown of a closed sprint keeps the tickets that left at the close.
    down = await report(client, board, "burndown", sprint=sprint["id"])
    assert down["rows"][-1]["remaining_hours"] == 7  # PA-1 3 h + PA-4 4 h


async def test_cfd_and_control_chart(
    client: AsyncClient, board: Team, clock: Clock, history: dict
) -> None:
    clock.set(at(16))
    cfd = await report(
        client, board, "cfd", project="PA", **{"from": "2026-09-07", "to": "2026-09-15"}
    )
    names = cfd["columns"][1:]
    assert names.index("To Do") < names.index("In Progress") < names.index("Done")
    by_day = {r["date"]: r for r in cfd["rows"]}
    assert (by_day["2026-09-08"]["To Do"], by_day["2026-09-08"]["Done"]) == (4, 0)
    assert (by_day["2026-09-09"]["To Do"], by_day["2026-09-09"]["Done"]) == (3, 1)
    assert by_day["2026-09-14"]["In Review"] == 1
    assert (by_day["2026-09-15"]["To Do"], by_day["2026-09-15"]["Done"]) == (2, 2)

    chart = await report(
        client, board, "control_chart", project="PA", **{"from": "2026-09-01", "to": "2026-09-16"}
    )
    assert [(r["key"], r["cycle_days"], r["lead_days"]) for r in chart["rows"]] == [
        ("PA-2", 0.08, 2.12),
        ("PA-3", 1.0, 8.0),
    ]
    assert chart["summary"]["p50_days"] == 0.08 and chart["summary"]["p85_days"] == 1.0


async def test_general_reports(
    client: AsyncClient, board: Team, clock: Clock, history: dict
) -> None:
    clock.set(at(18))
    cr = await report(
        client,
        board,
        "created_resolved",
        project="PA",
        **{"from": "2026-09-07", "to": "2026-09-15"},
    )
    by_day = {r["period"]: r for r in cr["rows"]}
    assert by_day["2026-09-07"]["created"] == 4
    assert by_day["2026-09-09"]["resolved"] == 1
    assert by_day["2026-09-15"]["cumulative_difference"] == 2
    weekly = await report(
        client,
        board,
        "created_resolved",
        project="PA",
        interval="week",
        **{"from": "2026-09-07", "to": "2026-09-18"},
    )
    assert [(r["created"], r["resolved"]) for r in weekly["rows"]] == [(4, 1), (0, 1)]

    dist = await report(client, board, "distribution", project="PA", field="area")
    assert [(r["value"], r["count"]) for r in dist["rows"]] == [("Backend", 3), ("Frontend", 1)]
    bugs = await report(client, board, "distribution", project="PA", field="area", q="type = bug")
    assert bugs["rows"] == []

    # 8 h done in the last 4 weeks = 2 h/week; 7 h left (PA-1 3 + PA-4 4) = 25 days.
    progress = await report(client, board, "milestone_progress", project="PA", milestone="V1")
    summary = progress["summary"]
    assert (summary["forecast_date"], summary["state"]) == ("2026-10-13", "on_track")
    assert summary["percent_by_hours"] == 40.0 and summary["percent_by_count"] == 50.0
    r = await client.patch(
        f"{API}/projects/PA/milestones/V1",
        headers=board.admin.headers,
        json={"target_date": "2026-10-01"},
    )
    assert r.status_code == 200
    progress = await report(client, board, "milestone_progress", project="PA", milestone="V1")
    assert progress["summary"]["state"] == "at_risk"

    time = await report(client, board, "time", project="PA")
    rows = {r["ticket"]: r for r in time["rows"]}
    assert (rows["PA-1"]["original_estimate_hours"], rows["PA-1"]["spent_hours"]) == (8, 2)
    assert [o["key"] for o in time["summary"]["over_estimate"]] == ["PA-3"]
    by_area = await report(client, board, "time", project="PA", by="area")
    assert {r["area"]: r["spent_hours"] for r in by_area["rows"]} == {"Backend": 6, "Frontend": 0}


async def test_report_errors_and_permissions(
    client: AsyncClient, board: Team, history: dict
) -> None:
    async def problem(kind: str, actor=None, **params: object) -> tuple[int, str]:  # type: ignore[no-untyped-def]
        r = await client.get(
            f"{API}/reports/{kind}", headers=(actor or board.viewer).headers, params=params
        )
        return r.status_code, r.json()["detail"]

    assert (await problem("nope", project="PA"))[0] == 422
    assert "sprint=<id>" in (await problem("burndown"))[1]
    assert "project=<key> or board=<id>" in (await problem("cfd"))[1]
    assert "Cannot group by" in (await problem("distribution", project="PA", field="color"))[1]
    assert (
        "does not exist" in (await problem("milestone_progress", project="PA", milestone="V9"))[1]
    )
    status, _ = await problem("cfd", board.outsider, project="PA")
    assert status == 404
    status, _ = await problem("burndown", board.outsider, sprint=history["sprint"]["id"])
    assert status == 404
    detail = (await problem("cfd", project="PA", **{"from": "2025-01-01", "to": "2026-09-01"}))[1]
    assert "up to 400" in detail


async def test_mcp_reports(
    client: AsyncClient, board: Team, clock: Clock, history: dict, mcp_for: McpFor
) -> None:
    clock.set(at(18))
    async with mcp_for(board.agent) as mcp:
        progress = payload(
            await mcp.call_tool("get_milestone_progress", {"project": "PA", "milestone": "V1"})
        )
        assert progress["state"] == "on_track" and progress["remaining_hours"] == 7
        burndown = payload(
            await mcp.call_tool(
                "get_report", {"type": "burndown", "sprint": history["sprint"]["id"]}
            )
        )
        rest = await report(client, board, "burndown", sprint=history["sprint"]["id"])
        assert burndown["summary"] == rest["summary"] and burndown["rows"] == rest["rows"]
        result = await mcp.call_tool("get_report", {"type": "velocity"})
        assert result.is_error
