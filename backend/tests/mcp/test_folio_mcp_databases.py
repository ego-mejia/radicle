"""Database tools over MCP (Folio 3.6): an agent fills the AI Tools inventory and reads it
back as a board."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_db_helpers import COLUMNS
from tests.integration.folio_helpers import API, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload


@pytest.fixture
async def inv(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "ai-tools", "name": "AI Tools"})
    await agent_can_write(client, team, "ai-tools")
    r = await client.post(
        f"{API}/nodes",
        headers=team.agent.headers,
        json={"space": "ai-tools", "kind": "database", "title": "Inventario"},
    )
    assert r.status_code == 201, r.text
    node = r.json()["id"]
    got = (await client.get(f"{API}/databases/{node}", headers=i)).json()
    board = {"name": "Board", "kind": "board", "group_by": "status"}
    r = await client.patch(
        f"{API}/databases/{node}",
        headers=i,
        json={"columns": COLUMNS, "views": [*got["views"], board]},
    )
    assert r.status_code == 200, r.text
    return str(node)


async def test_an_agent_fills_and_reads_the_inventory(
    client: AsyncClient, team: Team, inv: str
) -> None:
    rows = [
        {"Name": "Claude", "status": "Adopted", "seats": 12, "tags": ["ai"]},
        {"name": "Devin", "Status": "Idea"},
    ]
    async with folio_mcp(client, team.agent) as folio:
        added = payload(await folio.call_tool("add_database_rows", {"id": inv, "rows": rows}))
        assert added["added"] == 2
        out = payload(await folio.call_tool("query_database", {"id": inv}))
        assert out["title"] == "Inventario"
        assert [v["kind"] for v in out["views"]] == ["table", "board"]
        board = payload(await folio.call_tool("query_database", {"id": inv, "view": "board"}))
    assert board["view"] == "board"
    assert [(r["Name"], r["Status"]) for r in board["rows"]] == [
        ("Claude", "Adopted"),
        ("Devin", "Idea"),
    ]
    status = next(c for c in out["columns"] if c["name"] == "Status")
    assert [c["value"] for c in status["choices"]] == ["Idea", "Trial", "Adopted"]


async def test_wrong_rows_add_nothing_and_say_why(
    client: AsyncClient, team: Team, inv: str
) -> None:
    async with folio_mcp(client, team.agent) as folio:
        bad = [{"name": "ok"}, {"name": "x", "status": "Maybe"}]
        text = error_text(await folio.call_tool("add_database_rows", {"id": inv, "rows": bad}))
        assert "Row 2" in text and "No rows were added" in text, text
        text = error_text(
            await folio.call_tool("add_database_rows", {"id": inv, "rows": [{"Price": 3}]})
        )
        assert "Unknown columns: Price" in text and "Status" in text
        text = error_text(await folio.call_tool("add_database_rows", {"id": inv, "rows": []}))
        assert "between 1 and 100" in text
        text = error_text(await folio.call_tool("query_database", {"id": inv, "view": "nope"}))
        assert "view" in text.lower()
        assert payload(await folio.call_tool("query_database", {"id": inv}))["rows"] == []


async def test_readers_cannot_add_rows(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "database", "title": "Inv"}
    )
    node = r.json()["id"]
    async with folio_mcp(client, team.agent) as folio:
        assert payload(await folio.call_tool("query_database", {"id": node}))["rows"] == []
        rows = {"id": node, "rows": [{"name": "x"}]}
        text = error_text(await folio.call_tool("add_database_rows", rows))
    assert "edit" in text.lower(), text
