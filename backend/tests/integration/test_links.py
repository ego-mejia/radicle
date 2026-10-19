from httpx import AsyncClient

from tests.conftest import Team, new_ticket

API = "/api/v1"


async def link(client: AsyncClient, team: Team, source: str, type_: str, target: str):
    return await client.post(
        f"{API}/tickets/{source}/links",
        headers=team.member.headers,
        json={"type": type_, "target": target},
    )


async def test_acceptance_blocked_link_both_sides_and_warning(
    client: AsyncClient, board: Team
) -> None:
    for i in range(5):
        await new_ticket(client, board.member, title=f"T{i + 1}")
    r = await link(client, board, "PA-4", "blocks", "PA-5")
    assert r.status_code == 201
    assert [(x["label"], x["ticket"]["key"]) for x in r.json()] == [("blocks", "PA-5")]

    pa5 = (await client.get(f"{API}/tickets/PA-5", headers=board.viewer.headers)).json()
    assert [(x["label"], x["ticket"]["key"]) for x in pa5["links"]] == [("is blocked by", "PA-4")]
    assert pa5["blocked"] is True
    pa4 = (await client.get(f"{API}/tickets/PA-4", headers=board.viewer.headers)).json()
    assert pa4["blocked"] is False and pa4["links"][0]["label"] == "blocks"

    r = await client.post(
        f"{API}/tickets/PA-5/transitions",
        headers=board.member.headers,
        json={"to_status": "In Progress"},
    )
    assert r.status_code == 200
    assert r.json()["status"]["name"] == "In Progress"
    assert r.json()["warnings"] == [
        {
            "code": "blocked",
            "message": "Moved while blocked by PA-4, which are not done.",
            "by": ["PA-4"],
        }
    ]

    await client.post(
        f"{API}/tickets/PA-4/transitions",
        headers=board.member.headers,
        json={"to_status": "Done", "resolution": "wont_do"},
    )
    pa5 = (await client.get(f"{API}/tickets/PA-5", headers=board.viewer.headers)).json()
    assert pa5["blocked"] is False


async def test_all_link_labels(client: AsyncClient, board: Team) -> None:
    for i in range(4):
        await new_ticket(client, board.member, title=f"T{i + 1}")
    await link(client, board, "PA-1", "relates_to", "PA-2")
    await link(client, board, "PA-1", "duplicates", "PA-3")
    await link(client, board, "PA-4", "clones", "PA-1")
    r = await client.get(f"{API}/tickets/PA-1/links", headers=board.viewer.headers)
    assert [(x["label"], x["ticket"]["key"]) for x in r.json()] == [
        ("relates to", "PA-2"),
        ("duplicates", "PA-3"),
        ("is cloned by", "PA-4"),
    ]
    r = await client.get(f"{API}/tickets/PA-3/links", headers=board.viewer.headers)
    assert r.json()[0]["label"] == "is duplicated by"
    r = await client.get(f"{API}/tickets/PA-2/links", headers=board.viewer.headers)
    assert r.json()[0]["label"] == "relates to"


async def test_link_errors(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    assert (await link(client, board, "PA-1", "blocks", "PA-1")).status_code == 422
    assert (await link(client, board, "PA-1", "breaks", "PA-2")).status_code == 422
    r = await link(client, board, "PA-1", "blocks", "PA-99")
    assert r.status_code == 422 and "PA-99 not found" in r.json()["detail"]
    assert (await link(client, board, "PA-1", "relates_to", "PA-2")).status_code == 201
    r = await link(client, board, "PA-2", "relates_to", "PA-1")
    assert r.status_code == 409 and "already linked" in r.json()["detail"]
    r = await client.post(
        f"{API}/tickets/PA-1/links",
        headers=board.viewer.headers,
        json={"type": "blocks", "target": "PA-2"},
    )
    assert r.status_code == 403


async def test_remove_link_and_history(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    r = await link(client, board, "PA-1", "blocks", "PA-2")
    link_id = r.json()[0]["id"]
    assert (
        await client.delete(f"{API}/links/{link_id}", headers=board.viewer.headers)
    ).status_code == 403
    assert (
        await client.delete(f"{API}/links/{link_id}", headers=board.outsider.headers)
    ).status_code == 404
    assert (
        await client.delete(f"{API}/links/{link_id}", headers=board.member.headers)
    ).status_code == 204
    assert (
        await client.delete(f"{API}/links/{link_id}", headers=board.member.headers)
    ).status_code == 404
    r = await client.get(f"{API}/tickets/PA-2/history", headers=board.member.headers)
    events = [(e["event_type"], e["old_value"], e["new_value"]) for e in r.json()["items"][:2]]
    assert events == [
        ("link_removed", {"label": "is blocked by", "ticket": "PA-1"}, None),
        ("link_added", None, {"label": "is blocked by", "ticket": "PA-1"}),
    ]


async def test_deleted_tickets_disappear_from_links(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.member)
    await new_ticket(client, board.member)
    await link(client, board, "PA-1", "blocks", "PA-2")
    await client.delete(f"{API}/tickets/PA-1", headers=board.admin.headers)
    pa2 = (await client.get(f"{API}/tickets/PA-2", headers=board.member.headers)).json()
    assert pa2["links"] == [] and pa2["blocked"] is False
