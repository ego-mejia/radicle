from httpx import AsyncClient

from tests.conftest import Team, new_ticket

API = "/api/v1/tickets"


async def move(client: AsyncClient, team: Team, key: str, to: str, **extra: object):
    return await client.post(
        f"{API}/{key}/transitions", headers=team.member.headers, json={"to_status": to, **extra}
    )


async def test_acceptance_task_lifecycle(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await move(client, board, "PA-1", "In Review")
    assert r.status_code == 409
    assert "Valid targets" in r.json()["detail"]
    assert {v["name"] for v in r.json()["valid_transitions"]} == {"Start", "Close"}

    r = await move(client, board, "PA-1", "Done")
    assert r.status_code == 422
    assert r.json()["allowed_resolutions"] == ["duplicate", "wont_do"]

    r = await move(client, board, "PA-1", "Done", resolution="done")
    assert r.status_code == 422  # Close only allows wont_do or duplicate

    for status in ("In Progress", "In Review"):
        r = await move(client, board, "PA-1", status)
        assert r.status_code == 200 and r.json()["status"]["name"] == status

    r = await move(client, board, "PA-1", "Done")
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "resolution"
    r = await move(client, board, "PA-1", "Done", resolution="done")
    body = r.json()
    assert body["status"] == {"name": "Done", "category": "done"}
    assert body["resolution"] == "done" and body["resolved_at"] is not None

    r = await move(client, board, "PA-1", "To Do")
    body = r.json()
    assert body["status"]["name"] == "To Do"
    assert body["resolution"] is None and body["resolved_at"] is None


async def test_close_from_todo_with_wont_do(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await move(client, board, "PA-1", "Done", resolution="wont_do")
    assert r.status_code == 200 and r.json()["resolution"] == "wont_do"
    r = await client.get(f"{API}/PA-1/history", headers=board.member.headers)
    event = r.json()["items"][0]
    assert event["event_type"] == "status_changed"
    assert event["old_value"] == {"status": "To Do", "resolution": None}
    assert event["new_value"] == {"status": "Done", "resolution": "wont_do", "transition": "Close"}


async def test_get_transitions(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, type="bug", area="Frontend")
    r = await client.get(f"{API}/PA-1/transitions", headers=board.viewer.headers)
    assert r.json() == [
        {
            "name": "Start",
            "to_status": "In Progress",
            "category": "in_progress",
            "allowed_resolutions": None,
            "available": True,
            "reasons": [],
            "requires_comment": False,
        },
        {
            "name": "Close",
            "to_status": "Done",
            "category": "done",
            "allowed_resolutions": ["wont_do", "duplicate", "cannot_reproduce"],
            "available": True,
            "reasons": [],
            "requires_comment": False,
        },
    ]


async def test_draft_approve_sets_resolution_automatically(
    client: AsyncClient, board: Team
) -> None:
    await new_ticket(client, board.member, type="draft", area=None)
    await move(client, board, "PA-1", "In Review")
    r = await move(client, board, "PA-1", "Approved")
    assert r.status_code == 200 and r.json()["resolution"] == "done"


async def test_transition_needs_member(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    r = await client.post(
        f"{API}/PA-1/transitions", headers=board.viewer.headers, json={"to_status": "In Progress"}
    )
    assert r.status_code == 403
    r = await client.post(
        f"{API}/PA-1/transitions", headers=board.outsider.headers, json={"to_status": "In Progress"}
    )
    assert r.status_code == 404


async def test_transition_bumps_version_and_counts(client: AsyncClient, board: Team) -> None:
    t = await new_ticket(client, board.member, milestone="V1")
    r = await move(client, board, "PA-1", "In Progress")
    assert r.json()["version"] == t["version"] + 1
    r = await client.get("/api/v1/projects/PA/milestones/V1", headers=board.member.headers)
    assert r.json()["counts"] == {"todo": 0, "in_progress": 1, "done": 0}


async def test_change_draft_to_task(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member, type="draft", area=None)
    await move(client, board, "PA-1", "In Review")
    r = await client.post(f"{API}/PA-1/type", headers=board.member.headers, json={"type": "task"})
    assert r.status_code == 422 and "Area is required" in r.json()["detail"]
    r = await client.post(
        f"{API}/PA-1/type", headers=board.member.headers, json={"type": "task", "area": "Legal"}
    )
    body = r.json()
    assert r.status_code == 200
    assert body["type"] == "task" and body["status"]["name"] == "To Do" and body["area"] == "Legal"
    r = await client.get(f"{API}/PA-1/history", headers=board.member.headers)
    kinds = [(e["event_type"], e["field"]) for e in r.json()["items"][:3]]
    assert ("type_changed", "type") in kinds and ("status_changed", "status") in kinds
    assert ("field_changed", "area") in kinds
    type_event = next(e for e in r.json()["items"] if e["event_type"] == "type_changed")
    assert (type_event["old_value"], type_event["new_value"]) == ("draft", "task")


async def test_change_type_clears_resolution(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await move(client, board, "PA-1", "Done", resolution="duplicate")
    r = await client.post(f"{API}/PA-1/type", headers=board.member.headers, json={"type": "bug"})
    body = r.json()
    assert body["status"]["name"] == "Reported" and body["resolution"] is None
    r = await client.post(f"{API}/PA-1/type", headers=board.member.headers, json={"type": "bug"})
    assert r.status_code == 422 and "already a bug" in r.json()["detail"]
