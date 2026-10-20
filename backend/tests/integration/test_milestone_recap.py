"""The recap behind a milestone's celebration card."""

from httpx import AsyncClient

from tests.conftest import Team, new_ticket

API = "/api/v1"
RECAP = f"{API}/projects/PA/milestones/V1/recap"


PATHS = {
    "task": ("In Progress", "In Review", "Done"),
    "bug": ("In Progress", "QA Verified", "Done"),
}


async def finish(client: AsyncClient, team: Team, key: str, kind: str = "task") -> None:
    for status in PATHS[kind]:
        body: dict[str, object] = {"to_status": status}
        if status == "Done":
            body["resolution"] = "done"
        r = await client.post(
            f"{API}/tickets/{key}/transitions", headers=team.member.headers, json=body
        )
        assert r.status_code == 200, r.text


async def test_recap_counts_the_work_and_the_people(client: AsyncClient, board: Team) -> None:
    task = await new_ticket(client, board.member, milestone="V1", assignee=board.agent.handle)
    bug = await new_ticket(client, board.admin, milestone="V1", type="bug")
    await new_ticket(client, board.member, title="Elsewhere")
    await client.post(
        f"{API}/tickets/{task['key']}/worklogs", headers=board.member.headers, json={"minutes": 90}
    )
    await client.post(
        f"{API}/tickets/{bug['key']}/comments",
        headers=board.instance.headers,
        json={"body_md": "Seen it too"},
    )
    await finish(client, board, task["key"])

    r = await client.get(RECAP, headers=board.viewer.headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["complete"] is False and (body["tickets"], body["done"]) == (2, 1)
    assert (body["tasks"], body["bugs"], body["ideas"]) == (1, 1, 0)
    assert body["minutes_logged"] == 90 and body["comments"] == 1
    # Reporters, the agent assignee, the commenter and whoever logged time.
    assert (body["humans"], body["agents"]) == (3, 1)
    assert body["on_time"] is None and body["project_key"] == "PA"

    await finish(client, board, bug["key"], "bug")
    body = (await client.get(RECAP, headers=board.viewer.headers)).json()
    assert body["complete"] is True and body["days"] == 1
    assert body["on_time"] is True  # target date 2026-12-15
    assert body["finished_at"] is not None and len(body["people"]) == 4


async def test_recap_errors_and_permissions(client: AsyncClient, board: Team) -> None:
    r = await client.get(f"{API}/projects/PA/milestones/Nope/recap", headers=board.viewer.headers)
    assert r.status_code == 404 and "Milestone 'Nope' not found" in r.json()["detail"]
    r = await client.get(RECAP, headers=board.outsider.headers)
    assert r.status_code in (403, 404)
    body = (await client.get(RECAP, headers=board.viewer.headers)).json()
    assert body["complete"] is False and body["tickets"] == 0 and body["days"] is None
