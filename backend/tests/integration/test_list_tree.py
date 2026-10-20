"""Search rows say their parent and how many subtickets you can see, for nested lists."""

from httpx import AsyncClient

from tests.conftest import Team, new_ticket, patch_ticket

API = "/api/v1"


async def rows(client: AsyncClient, actor, q: str) -> dict[str, dict]:  # type: ignore[no-untyped-def]
    r = await client.get(f"{API}/tickets", headers=actor.headers, params={"q": q, "limit": 50})
    assert r.status_code == 200, r.text
    return {t["key"]: t for t in r.json()["items"]}


async def test_parent_and_child_count(client: AsyncClient, board: Team) -> None:
    m = board.member
    parent = (await new_ticket(client, m, title="Checkout revamp"))["key"]
    for title in ("Cart page", "Payment page"):
        await new_ticket(client, m, title=title, parent=parent)
    found = await rows(client, m, "project = PA")
    assert found[parent]["child_count"] == 2 and found[parent]["parent"] is None
    kids = [t for t in found.values() if t["parent"] == parent]
    assert len(kids) == 2 and all(k["child_count"] == 0 for k in kids)
    r = await client.get(f"{API}/tickets/{parent}/children", headers=m.headers)
    assert {c["parent"] for c in r.json()["items"]} == {parent}


async def test_restricted_parents_and_children_stay_hidden(
    client: AsyncClient, board: Team
) -> None:
    a, m = board.admin, board.member
    level = (
        await client.post(
            f"{API}/projects/PA/security-levels", headers=a.headers, json={"name": "Legal"}
        )
    ).json()
    assert level["name"] == "Legal"
    secret = (await new_ticket(client, a, title="Secret parent"))["key"]
    open_child = (await new_ticket(client, a, title="Open child", parent=secret))["key"]
    shown = (await new_ticket(client, a, title="Shown parent"))["key"]
    await new_ticket(client, a, title="Hidden child", parent=shown)
    hidden = next(
        k
        for k, t in (await rows(client, a, "project = PA")).items()
        if t["title"] == "Hidden child"
    )
    await patch_ticket(client, a, secret, security_level="Legal")
    await patch_ticket(client, a, hidden, security_level="Legal")

    found = await rows(client, m, "project = PA")
    assert found[open_child]["parent"] is None  # the parent's key does not leak
    assert found[shown]["child_count"] == 0  # the restricted child is not counted
