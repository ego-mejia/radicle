"""Databases over REST (Folio 3.6): columns and views, and the rows each view shows."""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from pydantic import Field

from radicle.folio.db.databases import FolioDatabase, FolioDbRow
from radicle.folio.db.models import FolioNode, FolioSpace
from radicle.folio.services import access, databases, db_rows, nodes
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import User

router = APIRouter(tags=["folio"])

ColumnType = Literal[
    "text", "number", "date", "select", "multi_select", "person", "checkbox", "url", "page"
]


class DatabaseColumn(Input):
    key: str | None = Field(default=None, description="Leave out for a new column")
    name: str
    type: ColumnType
    options: dict[str, Any] = Field(
        default_factory=dict, description='Selects: {"choices": [{"value", "color"}]}'
    )


class DatabaseFilter(Input):
    column: str
    op: Literal["eq", "neq", "contains", "gt", "gte", "lt", "lte", "empty", "not_empty"]
    value: Any = None


class DatabaseSort(Input):
    column: str
    direction: Literal["asc", "desc"] = "asc"


class DatabaseView(Input):
    id: str | None = Field(default=None, description="Leave out for a new view")
    name: str
    kind: Literal["table", "cards", "board"] = "table"
    group_by: str | None = Field(default=None, description="Boards: a select column's key")
    filters: list[DatabaseFilter] = Field(default_factory=list)
    sort: list[DatabaseSort] = Field(default_factory=list)
    visible_columns: list[str] | None = None


class DatabaseOut(Output):
    node_id: uuid.UUID
    title: str
    space: str
    can_edit: bool
    columns: list[dict[str, Any]]
    views: list[dict[str, Any]]
    cleared: int = Field(default=0, description="Values a column's new type could not keep")


class DatabasePatch(Input):
    columns: list[DatabaseColumn] | None = None
    views: list[DatabaseView] | None = None


class DbRowOut(Output):
    id: uuid.UUID
    values: dict[str, Any]
    updated_at: UtcDatetime


class DbRowsOut(Output):
    view: dict[str, Any]
    columns: list[dict[str, Any]]
    items: list[DbRowOut]


class DbRowIn(Input):
    values: dict[str, Any] = Field(default_factory=dict, description="By column key")
    after: uuid.UUID | None = Field(default=None, description="Place it after this row")


class DbRowPatch(Input):
    values: dict[str, Any] | None = Field(default=None, description="Only these; null clears")
    after: uuid.UUID | None = None
    to_top: bool = False


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


async def _out(
    db: Db, user: User, node: FolioNode, d: FolioDatabase, cleared: int = 0
) -> DatabaseOut:
    space = await db.get(FolioSpace, node.space_id)
    return DatabaseOut(
        node_id=node.id,
        title=node.title,
        space=space.key if space else "",
        can_edit=await access.may_edit(db, user, node),
        columns=d.columns,
        views=d.views,
        cleared=cleared,
    )


def _row(r: FolioDbRow) -> DbRowOut:
    return DbRowOut(id=r.id, values=r.values, updated_at=r.updated_at)


@router.get("/databases/{node_id}", response_model=DatabaseOut)
async def get_database(node_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> DatabaseOut:
    """Its columns and views, and whether you may change them."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    return await _out(db, principal.user, node, await databases.get_database(db, node))


@router.patch("/databases/{node_id}", response_model=DatabaseOut)
async def patch_database(
    node_id: uuid.UUID, body: DatabasePatch, principal: CurrentPrincipal, db: Db
) -> DatabaseOut:
    """Replace the columns and/or the views. A column's new type keeps what fits; `cleared`
    says how many values it couldn't."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    change = await databases.update_schema(
        db,
        principal.user,
        node,
        columns=[c.model_dump() for c in body.columns] if body.columns is not None else None,
        views=[v.model_dump() for v in body.views] if body.views is not None else None,
    )
    return await _out(db, principal.user, node, change.database, change.cleared)


@router.get("/databases/{node_id}/rows", response_model=DbRowsOut)
async def list_rows(
    node_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: Db,
    view: str | None = Query(default=None, description="A view's id; default the first"),
) -> DbRowsOut:
    """The rows the view shows, its filters and sort applied."""
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    database, shown, rows = await db_rows.query(db, principal.user, node, view)
    return DbRowsOut(view=shown, columns=database.columns, items=[_row(r) for r in rows])


@router.post("/databases/{node_id}/rows", response_model=DbRowOut, status_code=201)
async def add_row(
    node_id: uuid.UUID, body: DbRowIn, principal: CurrentPrincipal, db: Db
) -> DbRowOut:
    await _reader(db, principal)
    node = await nodes.get_node(db, principal.user, node_id)
    row = await db_rows.add_row(db, principal.user, node, body.values, after=body.after)
    return _row(row)


@router.patch("/rows/{row_id}", response_model=DbRowOut)
async def patch_row(
    row_id: uuid.UUID, body: DbRowPatch, principal: CurrentPrincipal, db: Db
) -> DbRowOut:
    """Change some values, or move it after another row (or to the top)."""
    await _reader(db, principal)
    row, node = await db_rows.get_row(db, principal.user, row_id)
    updated = await db_rows.update_row(
        db, principal.user, row, node, body.values, after=body.after, to_top=body.to_top
    )
    return _row(updated)


@router.delete("/rows/{row_id}", status_code=204)
async def delete_row(row_id: uuid.UUID, principal: CurrentPrincipal, db: Db) -> Response:
    await _reader(db, principal)
    row, node = await db_rows.get_row(db, principal.user, row_id)
    await db_rows.delete_row(db, principal.user, row, node)
    return Response(status_code=204)
