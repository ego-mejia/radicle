"""Database columns and views (Folio 3.6): types, validation and converting values when a
column changes type."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.databases import FolioDbRow
from radicle.folio.db.models import FolioNode
from radicle.folio.services import databases
from radicle.platform.errors import Forbidden, ValidationFailed
from tests.conftest import Team
from tests.integration.folio_db_helpers import COLUMNS, STATUS, inventory, user
from tests.integration.folio_helpers import API

__all__ = ["inventory"]  # the fixture


async def test_changing_a_column_type_converts_or_clears(
    db: AsyncSession, team: Team, inventory: FolioNode
) -> None:
    fernando = await user(db, team.instance.handle)
    await databases.update_schema(db, fernando, inventory, columns=COLUMNS)
    db.add(FolioDbRow(node_id=inventory.id, rank="a", values={"name": "12", "status": "Trial"}))
    db.add(FolioDbRow(node_id=inventory.id, rank="b", values={"name": "doce", "status": "Idea"}))
    columns = [
        {"key": "name", "name": "Name", "type": "number"},  # text → number
        {**STATUS, "options": {"choices": [{"value": "Trial"}]}},  # Idea removed
    ]  # seats and the rest removed
    change = await databases.update_schema(db, fernando, inventory, columns=columns)
    assert change.cleared == 2  # "doce" and Idea
    rows = (await db.scalars(select(FolioDbRow).order_by(FolioDbRow.rank))).all()
    assert [r.values for r in rows] == [{"name": 12, "status": "Trial"}, {}]
    view = change.database.views[0]
    assert view["visible_columns"] == ["name"]


async def test_schema_errors(db: AsyncSession, team: Team, inventory: FolioNode) -> None:
    fernando = await user(db, team.instance.handle)
    bad = [
        ([], None, "at least one column"),
        ([{"name": "X", "type": "money"}], None, "Column types"),
        ([{"key": "Mal", "name": "X", "type": "text"}], None, "lowercase"),
        (
            [
                {
                    "name": "S",
                    "type": "select",
                    "options": {"choices": [{"value": "a"}, {"value": "a"}]},
                }
            ],
            None,
            "repeated",
        ),
        (None, [{"name": "B", "kind": "board", "group_by": "name"}], "groups by a select"),
        (None, [{"name": "F", "filters": [{"column": "nope", "op": "eq"}]}], "A filter is"),
        (None, [], "at least one view"),
    ]
    for columns, views, says in bad:
        with pytest.raises(ValidationFailed, match=says):
            await databases.update_schema(db, fernando, inventory, columns=columns, views=views)


async def test_not_a_database(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Página"}
    )
    page = await db.get(FolioNode, uuid.UUID(r.json()["id"]))
    assert page is not None
    with pytest.raises(ValidationFailed, match="not a database"):
        await databases.get_database(db, page)
    db_node = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "database", "title": "Tabla"}
    )
    r = await client.get(f"{API}/nodes/{db_node.json()['id']}/draft", headers=i)
    assert r.status_code == 422 and "rows, not a draft" in r.json()["detail"]
    r = await client.post(f"{API}/nodes/{db_node.json()['id']}/publish", headers=i, json={})
    assert r.status_code == 422


async def test_only_editors_change_the_schema(
    db: AsyncSession, team: Team, inventory: FolioNode
) -> None:
    luis = await user(db, team.member.handle)
    with pytest.raises(Forbidden):
        await databases.update_schema(db, luis, inventory, columns=COLUMNS)
