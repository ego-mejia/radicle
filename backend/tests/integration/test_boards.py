import pytest
from httpx import AsyncClient

from tests.conftest import Team, make_project, new_ticket
from tests.mcp.conftest import McpFor, payload
from tests.mcp.conftest import mcp_for as mcp_for  # the fixture

API = "/api/v1"


async def main_board(client: AsyncClient, team: Team, key: str = "PA") -> dict:
    r = await client.get(f"{API}/projects/{key}/boards", headers=team.viewer.headers)
    assert r.status_code == 200, r.text
    return r.json()["items"][0]


async def data(client: AsyncClient, actor, board: dict, **params: object) -> dict:  # type: ignore[no-untyped-def]
    r = await client.get(f"{API}/boards/{board['id']}/data", headers=actor.headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def status_ids(board: dict, *names: str) -> list[str]:
    return [s["id"] for s in board["statuses"] if s["name"] in names]


async def move(client: AsyncClient, actor, board: dict, **body: object):  # type: ignore[no-untyped-def]
    return await client.post(f"{API}/boards/{board['id']}/move", headers=actor.headers, json=body)


@pytest.fixture
async def review_board(client: AsyncClient, board: Team) -> dict:
    """PA's Main board turned into To Do | Doing | Review (WIP 3) | Done."""
    main = await main_board(client, board)
    columns = [
        {"name": "To Do", "categories": ["todo"]},
        {"name": "Doing", "status_ids": status_ids(main, "In Progress")},
        {
            "name": "Review",
            "status_ids": status_ids(main, "In Review", "QA Verified"),
            "wip_limit": 3,
        },
        {"name": "Done", "categories": ["done"]},
    ]
    r = await client.patch(
        f"{API}/boards/{main['id']}", headers=board.admin.headers, json={"columns": columns}
    )
    assert r.status_code == 200, r.text
    return r.json()


async def to_review(client: AsyncClient, team: Team, key: str, kind: str = "task") -> None:
    statuses = ("In Progress", "In Review") if kind == "task" else ("In Progress", "QA Verified")
    for status in statuses:
        r = await client.post(
            f"{API}/tickets/{key}/transitions",
            headers=team.member.headers,
            json={"to_status": status},
        )
        assert r.status_code == 200, r.text


async def test_main_board_is_created_with_projects(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    assert main["name"] == "Main" and main["kind"] == "kanban"
    assert [c["name"] for c in main["columns"]] == ["To Do", "In Progress", "In Review", "Done"]
    review = main["columns"][2]
    assert sorted(review["status_ids"]) == sorted(status_ids(main, "In Review", "QA Verified"))
    assert [q["name"] for q in main["quick_filters"]] == [
        "My tickets",
        "Only bugs",
        "#backlog",
        "Blocked",
    ]
    assert main["unmapped_statuses"] == []
    assert main["card_fields"][:3] == ["area", "milestone", "children"]


async def test_in_progress_to_in_review_on_the_main_board(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    await new_ticket(client, board.member)
    r = await client.post(
        f"{API}/tickets/PA-1/transitions",
        headers=board.member.headers,
        json={"to_status": "In Progress"},
    )
    assert r.status_code == 200, r.text
    r = await move(client, board.member, main, ticket="PA-1", column=2)
    assert r.status_code == 200, r.text
    assert r.json()["ticket"]["status"]["name"] == "In Review"
    columns = (await data(client, board.viewer, main))["columns"]
    assert [t["key"] for t in columns[2]["tickets"]] == ["PA-1"]


async def test_acceptance_review_column_with_wip_3(
    client: AsyncClient, board: Team, review_board: dict
) -> None:
    assert review_board["unmapped_statuses"] == []
    for i in range(4):
        kind = "bug" if i % 2 else "task"
        await new_ticket(client, board.member, type=kind, title=f"t{i}")
        if i < 3:
            await to_review(client, board, f"PA-{i + 1}", kind)
    result = await data(client, board.viewer, review_board)
    review = result["columns"][2]
    assert (review["name"], review["count"], review["over_limit"]) == ("Review", 3, False)
    assert {t["status"]["name"] for t in review["tickets"]} == {"In Review", "QA Verified"}

    # Soft limit: the fourth card is accepted and the column turns red.
    await to_review(client, board, "PA-4", "bug")
    review = (await data(client, board.viewer, review_board))["columns"][2]
    assert review["count"] == 4 and review["over_limit"] is True


async def test_move_between_columns(client: AsyncClient, board: Team, review_board: dict) -> None:
    await new_ticket(client, board.member)
    r = await move(client, board.member, review_board, ticket="PA-1", column=2)
    assert r.status_code == 409 and r.json()["type"].endswith("column_rejects")
    r = await move(client, board.member, review_board, ticket="PA-1", column=1)
    assert r.status_code == 200 and r.json()["ticket"]["status"]["name"] == "In Progress"
    r = await move(client, board.member, review_board, ticket="PA-1", column=3)
    assert r.status_code == 422 and r.json()["type"].endswith("resolution_required")
    r = await move(
        client,
        board.member,
        review_board,
        ticket="PA-1",
        column=3,
        transition="Close",
        resolution="wont_do",
    )
    assert r.status_code == 200 and r.json()["ticket"]["status"]["name"] == "Done"
    r = await move(client, board.member, review_board, ticket="PA-1", column=9)
    assert r.status_code == 422
    r = await move(client, board.viewer, review_board, ticket="PA-1", column=0)
    assert r.status_code == 403


async def test_hard_wip_limit_and_admin_force(
    client: AsyncClient, board: Team, review_board: dict
) -> None:
    r = await client.patch(
        f"{API}/boards/{review_board['id']}", headers=board.admin.headers, json={"wip_mode": "hard"}
    )
    for i in range(4):
        await new_ticket(client, board.member, title=f"t{i}")
        await client.post(
            f"{API}/tickets/PA-{i + 1}/transitions",
            headers=board.member.headers,
            json={"to_status": "In Progress"},
        )
    for i in range(3):
        r = await move(client, board.member, review_board, ticket=f"PA-{i + 1}", column=2)
        assert r.status_code == 200
    r = await move(client, board.member, review_board, ticket="PA-4", column=2, force=True)
    assert r.status_code == 409 and r.json()["type"].endswith("wip_limit_reached")
    r = await move(client, board.admin, review_board, ticket="PA-4", column=2, force=True)
    assert r.status_code == 200
    history = (await client.get(f"{API}/tickets/PA-4/history", headers=board.member.headers)).json()
    assert history["items"][0]["new_value"]["wip_forced"] == "Review"


async def test_cards_count_their_subtickets(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    parent = await new_ticket(client, board.member, title="Parent")
    for i in range(2):
        await new_ticket(client, board.member, title=f"child {i}", parent=parent["key"])
    todo = (await data(client, board.member, main))["columns"][0]["tickets"]
    counts = {t["key"]: t["child_count"] for t in todo}
    assert counts[parent["key"]] == 2
    assert counts["PA-2"] == 0


async def test_rank_within_a_column(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    for i in range(3):
        await new_ticket(client, board.member, title=f"t{i}")
    r = await move(client, board.member, main, ticket="PA-3", column=0, before="PA-1")
    assert r.status_code == 200
    todo = (await data(client, board.member, main))["columns"][0]
    assert [t["key"] for t in todo["tickets"]] == ["PA-3", "PA-1", "PA-2"]


async def test_swimlanes_and_quick_filters(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    await new_ticket(
        client, board.member, type="bug", area="Frontend", assignee="luis", priority="high"
    )
    await new_ticket(client, board.member, area="Backend", milestone="V1", parent=None)
    await new_ticket(client, board.member, area="Backend", parent="PA-2", tags=["backlog"])
    by_area = await data(client, board.viewer, main, swimlane="area")
    assert [(lane["label"], lane["count"]) for lane in by_area["lanes"]] == [
        ("Backend", 2),
        ("Frontend", 1),
    ]
    cards = {t["key"]: t["lane"] for t in by_area["columns"][0]["tickets"]}
    assert cards["PA-1"] != cards["PA-2"] and cards["PA-2"] == cards["PA-3"]
    by_parent = await data(client, board.viewer, main, swimlane="parent")
    assert [lane["label"] for lane in by_parent["lanes"]] == ["PA-2 Ticket", ""]
    for option in ("assignee", "priority", "milestone", "type", "none"):
        result = await data(client, board.viewer, main, swimlane=option)
        assert sum(c["count"] for c in result["columns"]) == 3
    by_priority = await data(client, board.viewer, main, swimlane="priority")
    assert [lane["label"] for lane in by_priority["lanes"]] == ["high", "medium"]

    filters = {q["name"]: q["id"] for q in main["quick_filters"]}
    bugs = await data(client, board.member, main, quick_filters=[filters["Only bugs"]])
    assert [t["key"] for t in bugs["columns"][0]["tickets"]] == ["PA-1"]
    both = await data(
        client, board.member, main, quick_filters=[filters["Only bugs"], filters["#backlog"]]
    )
    assert both["columns"][0]["count"] == 0
    mine = await data(client, board.member, main, quick_filters=[filters["My tickets"]])
    assert [t["key"] for t in mine["columns"][0]["tickets"]] == ["PA-1"]


async def test_done_window_and_unmapped_statuses(client: AsyncClient, board: Team) -> None:
    main = await main_board(client, board)
    await new_ticket(client, board.member)
    await client.post(
        f"{API}/tickets/PA-1/transitions",
        headers=board.member.headers,
        json={"to_status": "Done", "resolution": "wont_do"},
    )
    assert (await data(client, board.viewer, main))["columns"][3]["count"] == 1
    columns = [
        {"name": "Open", "categories": ["todo", "in_progress"]},
        {"name": "Done", "categories": ["done"]},
    ]
    r = await client.patch(
        f"{API}/boards/{main['id']}",
        headers=board.admin.headers,
        json={"columns": columns[:1]},
    )
    assert {s["category"] for s in r.json()["unmapped_statuses"]} == {"done"}


async def test_board_crud_validation_and_visibility(client: AsyncClient, board: Team) -> None:
    r = await client.post(
        f"{API}/projects/PA/boards",
        headers=board.admin.headers,
        json={"name": "Backend", "source_rql": "project = PA AND area = Backend"},
    )
    assert r.status_code == 201
    backend = r.json()
    await new_ticket(client, board.member, area="Backend")
    await new_ticket(client, board.member, area="Legal")
    result = await data(client, board.member, backend)
    assert [t["key"] for t in result["columns"][0]["tickets"]] == ["PA-1"]

    bad = [
        ({"columns": []}, "at least one column"),
        ({"columns": [{"name": "A"}, {"name": "a"}]}, "unique"),
        (
            {"columns": [{"name": "A", "status_ids": ["00000000-0000-0000-0000-00000000000f"]}]},
            "not in this board",
        ),
        ({"columns": [{"name": "A", "wip_limit": 0}]}, "WIP limit"),
        ({"source_rql": "type = = bug"}, "not valid RQL"),
        ({"card_fields": ["color"]}, "Unknown card fields"),
        ({"done_window_days": 0}, "between 1 and 365"),
        ({"name": " "}, "Board names"),
    ]
    for body, message in bad:
        r = await client.patch(
            f"{API}/boards/{backend['id']}", headers=board.admin.headers, json=body
        )
        assert r.status_code == 422, body
        assert message in r.json()["detail"], (body, r.json()["detail"])
    r = await client.patch(
        f"{API}/boards/{backend['id']}", headers=board.member.headers, json={"name": "X"}
    )
    assert r.status_code == 403
    r = await client.get(f"{API}/boards/{backend['id']}", headers=board.outsider.headers)
    assert r.status_code == 404

    r = await client.post(
        f"{API}/boards/{backend['id']}/quick-filters",
        headers=board.admin.headers,
        json={"name": "Altas", "rql": "priority >= high"},
    )
    assert r.status_code == 201
    qf = r.json()
    r = await client.patch(
        f"{API}/boards/{backend['id']}/quick-filters/{qf['id']}",
        headers=board.admin.headers,
        json={"name": "Altas", "rql": "priority = highest", "position": 0},
    )
    assert r.json()["rql"] == "priority = highest"
    r = await client.get(
        f"{API}/boards/{backend['id']}/quick-filters", headers=board.viewer.headers
    )
    assert r.json()["items"][0]["name"] == "Altas"
    r = await client.delete(
        f"{API}/boards/{backend['id']}/quick-filters/{qf['id']}", headers=board.admin.headers
    )
    assert r.status_code == 204
    r = await client.delete(f"{API}/boards/{backend['id']}", headers=board.admin.headers)
    assert r.status_code == 204


async def test_tickets_you_cannot_see_never_show(client: AsyncClient, board: Team) -> None:
    await make_project(client, board.instance, "PB")
    await client.post(
        f"{API}/projects/PB/areas", headers=board.instance.headers, json={"name": "Ops"}
    )
    await client.post(
        f"{API}/projects/PB/tickets",
        headers=board.instance.headers,
        json={"type": "task", "title": "Secreto", "area": "Ops"},
    )
    await new_ticket(client, board.member)
    main = await main_board(client, board)
    r = await client.patch(
        f"{API}/boards/{main['id']}",
        headers=board.admin.headers,
        json={"source_rql": "project IN (PA, PB)"},
    )
    assert r.status_code == 200
    seen = await data(client, board.member, main)
    assert [t["key"] for t in seen["columns"][0]["tickets"]] == ["PA-1"]
    everything = await data(client, board.instance, main)
    assert len(everything["columns"][0]["tickets"]) == 2


async def test_mcp_boards(client: AsyncClient, board: Team, mcp_for: McpFor) -> None:
    await new_ticket(client, board.member, type="bug", area="Frontend")
    await new_ticket(client, board.member)
    async with mcp_for(board.agent) as mcp:
        listed = payload(await mcp.call_tool("list_boards", {"project": "PA"}))
        assert listed[0]["name"] == "Main"
        view = payload(
            await mcp.call_tool(
                "get_board", {"board": listed[0]["id"], "quick_filters": ["Only bugs"]}
            )
        )
        assert [t["key"] for t in view["columns"][0]["tickets"]] == ["PA-1"]
        assert view["columns"][0]["count"] == 1


async def test_several_transitions_ask_which(
    client: AsyncClient, board: Team, review_board: dict
) -> None:
    await new_ticket(client, board.member)
    await to_review(client, board, "PA-1")
    r = await move(client, board.member, review_board, ticket="PA-1", column=3)
    assert r.status_code == 409 and r.json()["type"].endswith("choose_transition")
    assert {o["name"] for o in r.json()["options"]} == {"Complete", "Close"}
    r = await move(
        client,
        board.member,
        review_board,
        ticket="PA-1",
        column=3,
        transition="Complete",
        resolution="done",
    )
    assert r.json()["ticket"]["resolution"] == "done"


async def test_a_status_named_in_a_column_wins_over_its_category(
    client: AsyncClient, board: Team
) -> None:
    main = await main_board(client, board)
    review = {"name": "Review", "status_ids": status_ids(main, "In Review")}
    by_category = [
        {"name": c["name"], "categories": c["categories"]}
        for c in main["columns"]
        if c["categories"]
    ]
    await new_ticket(client, board.member)
    await to_review(client, board, "PA-1")
    await new_ticket(client, board.member)
    await to_review(client, board, "PA-2", kind="task")
    r = await client.post(
        f"{API}/tickets/PA-2/transitions",
        headers=board.member.headers,
        json={"to_status": "In Progress"},
    )
    assert r.status_code == 200, r.text

    async def where_is(columns: list) -> dict[str, list[str]]:  # type: ignore[type-arg]
        r = await client.patch(
            f"{API}/boards/{main['id']}", headers=board.admin.headers, json={"columns": columns}
        )
        assert r.status_code == 200, r.text
        result = await data(client, board.viewer, main)
        return {
            c["name"]: [t["key"] for t in c["tickets"]] for c in result["columns"] if c["tickets"]
        }

    # Wherever Review sits, In Review tickets go there and not to the category column.
    assert await where_is([by_category[0], review, *by_category[1:]]) == {
        "Review": ["PA-1"],
        "In Progress": ["PA-2"],
    }
    columns = [*by_category[:2], review, by_category[2]]
    assert await where_is(columns) == {"In Progress": ["PA-2"], "Review": ["PA-1"]}
    r = await client.get(f"{API}/boards/{main['id']}", headers=board.viewer.headers)
    assert r.json()["unmapped_statuses"] == []

    # And a card moves from In Progress to that Review column.
    r = await move(client, board.member, main, ticket="PA-2", column=2)
    assert r.status_code == 200, r.text
    assert r.json()["ticket"]["status"]["name"] == "In Review"
