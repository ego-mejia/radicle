"""Database tools (Folio 3.6): an agent reads a view's rows and adds rows, by column name."""

from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from radicle.folio.mcp.read import NodeId
from radicle.platform.mcp.api import api


def _keyed(columns: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
    """A row's values by column key, from column names (any case) or keys."""
    keys = {c["key"]: c["key"] for c in columns} | {c["name"].lower(): c["key"] for c in columns}
    unknown = [name for name in row if (keys.get(name) or keys.get(name.lower())) is None]
    if unknown:
        names = ", ".join(c["name"] for c in columns)
        raise ToolError(f"Unknown columns: {', '.join(unknown)}. The columns are: {names}.")
    return {keys.get(name) or keys[name.lower()]: value for name, value in row.items()}


def register(server: MCPServer) -> None:
    @server.tool()
    async def query_database(
        ctx: Context,
        id: NodeId,
        view: Annotated[str | None, Field(description="A view's id; default the first")] = None,
    ) -> dict[str, Any]:
        """A database's rows as one of its views shows them (its filters and sort), each
        keyed by column name, plus its columns and views."""
        async with api(ctx) as client:
            database = await client.call("GET", f"/folio/databases/{id}")
            rows = await client.call("GET", f"/folio/databases/{id}/rows", params={"view": view})
        names = {c["key"]: c["name"] for c in rows["columns"]}
        return {
            "title": database["title"],
            "columns": [
                {"name": c["name"], "type": c["type"], **c.get("options", {})}
                for c in rows["columns"]
            ],
            "views": [
                {"id": v["id"], "name": v["name"], "kind": v["kind"]} for v in database["views"]
            ],
            "view": rows["view"]["id"],
            "rows": [
                {"id": r["id"], **{names.get(k, k): v for k, v in r["values"].items()}}
                for r in rows["items"]
            ],
        }

    @server.tool()
    async def add_database_rows(
        ctx: Context,
        id: NodeId,
        rows: Annotated[
            list[dict[str, Any]],
            Field(description="Up to 100 rows, values by column name; a select takes a choice"),
        ],
    ) -> dict[str, Any]:
        """Add rows at the end of a database, all or none: a wrong value names its row
        and column. query_database shows the columns and their choices."""
        async with api(ctx) as client:
            database = await client.call("GET", f"/folio/databases/{id}")
            body = {"rows": [_keyed(database["columns"], row) for row in rows]}
            out = await client.call("POST", f"/folio/databases/{id}/rows/batch", json=body)
        return {"added": len(out["items"]), "ids": [r["id"] for r in out["items"]]}
