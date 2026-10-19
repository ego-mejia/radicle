from datetime import timedelta

from httpx import AsyncClient

from radicle.services import periods
from tests.conftest import Team, new_ticket, patch_ticket

API = "/api/v1"


async def timeline(client: AsyncClient, team: Team, **params: object) -> dict:
    r = await client.get(f"{API}/projects/PA/timeline", headers=team.viewer.headers, params=params)
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


async def set_target(client: AsyncClient, team: Team, day: str) -> None:
    r = await client.patch(
        f"{API}/projects/PA/milestones/V1", headers=team.admin.headers, json={"target_date": day}
    )
    assert r.status_code == 200, r.text


async def test_groups_undated_and_dependencies(client: AsyncClient, board: Team) -> None:
    await new_ticket(
        client, board.member, milestone="V1", start_date="2026-11-02", due_date="2026-11-06"
    )
    await new_ticket(
        client, board.member, milestone="V1", start_date="2026-11-05", due_date="2026-11-10"
    )
    await new_ticket(client, board.member, due_date="2026-11-20")
    await new_ticket(client, board.member, title="sin fechas")
    r = await client.post(
        f"{API}/tickets/PA-1/links",
        headers=board.member.headers,
        json={"type": "blocks", "target": "PA-2"},
    )
    assert r.status_code == 201, r.text

    data = await timeline(client, board)
    assert [g["label"] for g in data["groups"]] == ["V1", ""]
    v1 = data["groups"][0]
    assert v1["milestone"]["target_date"] == "2026-12-15"
    assert [t["key"] for t in v1["tickets"]] == ["PA-1", "PA-2"]
    assert v1["tickets"][0]["version"] >= 1
    assert [t["key"] for t in data["undated"]] == ["PA-4"]
    # PA-1 ends on the 6th, PA-2 starts on the 5th: impossible.
    assert data["dependencies"] == [{"blocker": "PA-1", "blocked": "PA-2", "conflict": True}]

    r = await patch_ticket(client, board.member, "PA-2", start_date="2026-11-07")
    assert r.status_code == 200
    assert (await timeline(client, board))["dependencies"][0]["conflict"] is False

    by_area = await timeline(client, board, group_by="area", q="due >= 2026-11-15")
    assert [(g["label"], [t["key"] for t in g["tickets"]]) for g in by_area["groups"]] == [
        ("Backend", ["PA-3"])
    ]
    window = await timeline(client, board, **{"from": "2026-11-08", "to": "2026-11-30"})
    dated = [t["key"] for g in window["groups"] for t in g["tickets"]]
    assert dated == ["PA-2", "PA-3"]


async def test_dates_change_with_history(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, start_date="2026-11-02", due_date="2026-11-06")
    r = await patch_ticket(
        client, board.member, "PA-1", start_date="2026-11-09", due_date="2026-11-13"
    )
    assert r.status_code == 200, r.text
    events = (await client.get(f"{API}/tickets/PA-1/history", headers=board.viewer.headers)).json()[
        "items"
    ]
    changed = {
        e["field"]: (e["old_value"], e["new_value"])
        for e in events
        if e["event_type"] == "field_changed"
    }
    assert changed["start_date"] == ("2026-11-02", "2026-11-09")
    assert changed["due_date"] == ("2026-11-06", "2026-11-13")


async def test_milestone_forecast(client: AsyncClient, board: Team) -> None:
    today = periods.today()
    for i in range(3):
        await new_ticket(client, board.member, title=f"t{i}", milestone="V1", estimate_hours=10)
    v1 = (await timeline(client, board))["groups"][0]["milestone"]
    assert v1["state"] == "no_forecast" and v1["forecast_date"] is None

    await finish(client, board, "PA-1")
    # 10 h done in the last 4 weeks = 2.5 h/week; 20 h left = 8 weeks.
    expected = today + timedelta(days=56)
    await set_target(client, board, (today + timedelta(days=30)).isoformat())
    v1 = (await timeline(client, board))["groups"][0]["milestone"]
    assert v1["forecast_date"] == expected.isoformat()
    assert v1["state"] == "at_risk" and v1["percent_by_hours"] == 33.3
    await set_target(client, board, (today + timedelta(days=60)).isoformat())
    assert (await timeline(client, board))["groups"][0]["milestone"]["state"] == "on_track"


async def test_timeline_permissions(client: AsyncClient, board: Team) -> None:
    r = await client.get(f"{API}/projects/PA/timeline", headers=board.outsider.headers)
    assert r.status_code == 404
    r = await client.get(
        f"{API}/projects/PA/timeline", headers=board.viewer.headers, params={"q": "nope ="}
    )
    assert r.status_code == 422
