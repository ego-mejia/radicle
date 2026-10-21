"""Database rows and views (Folio 3.6). Acceptance: the AI Tools inventory, seen as a board
grouped by status."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode
from radicle.folio.services import databases, db_rows
from radicle.platform.errors import Forbidden, NotFound, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_db_helpers import COLUMNS, inventory, user
from tests.integration.folio_helpers import API

__all__ = ["inventory"]  # the fixture


async def test_acceptance_the_inventory_as_a_board(
    db: AsyncSession, team: Team, inventory: FolioNode
) -> None:
    fernando = await user(db, team.instance.handle)
    first = await databases.get_database(db, inventory)
    assert [c["key"] for c in first.columns] == ["name"]
    board = {
        "name": "Por estado",
        "kind": "board",
        "group_by": "status",
        "sort": [{"column": "name"}],
    }
    change = await databases.update_schema(
        db, fernando, inventory, columns=COLUMNS, views=[*first.views, board]
    )
    keys = [c["key"] for c in change.database.columns]
    assert keys == ["name", "status", "owner", "seats", "since", "link", "tags", "paid"]
    for name, status in (("Claude", "Adopted"), ("Cursor", "Trial"), ("Devin", "Idea")):
        await db_rows.add_row(db, fernando, inventory, {"name": name, "status": status})
    await db_rows.add_row(
        db,
        fernando,
        inventory,
        {
            "name": "Copilot",
            "status": "Adopted",
            "owner": "@Fernando",
            "seats": "12",
            "since": "2026-01-15",
            "link": "https://github.com/features/copilot",
            "tags": ["ai", "ai"],
            "paid": True,
        },
    )
    _, view, rows = await db_rows.query(db, fernando, inventory, "por_estado")
    assert view["kind"] == "board" and view["group_by"] == "status"
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(row.values["status"], []).append(row.values["name"])
    assert groups == {"Adopted": ["Claude", "Copilot"], "Trial": ["Cursor"], "Idea": ["Devin"]}
    copilot = next(r for r in rows if r.values["name"] == "Copilot")
    assert copilot.values["owner"] == "fernando" and copilot.values["seats"] == 12
    assert copilot.values["tags"] == ["ai"]


@pytest.mark.parametrize(
    ("values", "says"),
    [
        ({"status": "Nope"}, "Status is one of: Idea, Trial, Adopted"),
        ({"owner": "@nadie"}, "@nadie isn't"),
        ({"seats": "many"}, "Seats is a number"),
        ({"since": "ayer"}, "YYYY-MM-DD"),
        ({"link": "ftp://x"}, "http or https"),
        ({"tags": ["ml"]}, "Tags is a list of: ai"),
        ({"paid": "yes"}, "true or false"),
        ({"color": "red"}, "Unknown columns: color"),
    ],
)
async def test_values_are_checked_by_column(
    db: AsyncSession, team: Team, inventory: FolioNode, values: dict, says: str
) -> None:
    fernando = await user(db, team.instance.handle)
    await databases.update_schema(db, fernando, inventory, columns=COLUMNS)
    with pytest.raises(ValidationFailed, match=says):
        await db_rows.add_row(db, fernando, inventory, values)


async def test_filters_and_sort(db: AsyncSession, team: Team, inventory: FolioNode) -> None:
    fernando = await user(db, team.instance.handle)
    await databases.update_schema(db, fernando, inventory, columns=COLUMNS)
    for name, seats in (("b", 5), ("a", 20), ("c", None), ("d", 9)):
        await db_rows.add_row(db, fernando, inventory, {"name": name, "seats": seats})
    view = {
        "name": "Grandes",
        "filters": [{"column": "seats", "op": "gte", "value": 6}],
        "sort": [{"column": "seats", "direction": "desc"}],
    }
    database = await databases.get_database(db, inventory)
    await databases.update_schema(db, fernando, inventory, views=[*database.views, view])
    _, _, rows = await db_rows.query(db, fernando, inventory, "grandes")
    assert [r.values["name"] for r in rows] == ["a", "d"]
    by_name = {"name": "Por nombre", "sort": [{"column": "seats"}]}
    await databases.update_schema(db, fernando, inventory, views=[*database.views, by_name])
    _, _, rows = await db_rows.query(db, fernando, inventory, "por_nombre")
    assert [r.values["name"] for r in rows] == ["b", "d", "a", "c"]  # empty last
    empty = {"name": "Sin", "filters": [{"column": "seats", "op": "empty"}]}
    await databases.update_schema(db, fernando, inventory, views=[*database.views, empty])
    assert [r.values["name"] for r in (await db_rows.query(db, fernando, inventory, "sin"))[2]] == [
        "c"
    ]


async def test_rows_move_and_go(db: AsyncSession, team: Team, inventory: FolioNode) -> None:
    fernando = await user(db, team.instance.handle)
    a = await db_rows.add_row(db, fernando, inventory, {"name": "a"})
    b = await db_rows.add_row(db, fernando, inventory, {"name": "b"})
    c = await db_rows.add_row(db, fernando, inventory, {"name": "c"}, after=a.id)
    names = lambda rows: [r.values["name"] for r in rows]  # noqa: E731
    assert names((await db_rows.query(db, fernando, inventory))[2]) == ["a", "c", "b"]
    await db_rows.update_row(db, fernando, b, inventory, to_top=True)
    await db_rows.update_row(db, fernando, c, inventory, {"name": None})
    await db_rows.delete_row(db, fernando, a, inventory)
    rows = (await db_rows.query(db, fernando, inventory))[2]
    assert [r.values.get("name") for r in rows] == ["b", None]


async def test_permissions_follow_the_node(
    client: AsyncClient, db: AsyncSession, team: Team, inventory: FolioNode
) -> None:
    fernando = await user(db, team.instance.handle)
    luis = await user(db, team.member.handle)
    row = await db_rows.add_row(db, fernando, inventory, {"name": "Claude"})
    _, _, rows = await db_rows.query(db, luis, inventory)  # readers read
    assert len(rows) == 1
    with pytest.raises(Forbidden):
        await db_rows.add_row(db, luis, inventory, {"name": "x"})
    r = await client.put(
        f"{API}/nodes/{inventory.id}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": fernando.handle}]},
    )
    assert r.status_code == 200, r.text
    with pytest.raises(NotFound):
        await db_rows.query(db, luis, inventory)
    with pytest.raises(NotFound):
        await db_rows.get_row(db, luis, row.id)
