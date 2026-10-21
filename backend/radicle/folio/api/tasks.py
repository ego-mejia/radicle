"""Mis tareas over REST (Folio 2.4): your action items, and checking them off."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.api.spaces import NodeRef, _ref
from radicle.folio.services import actions
from radicle.folio.services.notices import node_link
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Input, Output, UtcDatetime

router = APIRouter(tags=["folio"])


class FolioTaskOut(Output):
    id: uuid.UUID
    text: str
    done: bool
    due: date | None
    bucket: Literal["overdue", "today", "upcoming", "no_date"]
    node: NodeRef
    url: str = Field(description="The document holding the item")
    updated_at: UtcDatetime


class FolioTasksOut(Output):
    items: list[FolioTaskOut]


class ActionItemPatch(Input):
    done: bool


def _out(task: actions.Task) -> FolioTaskOut:
    item = task.item
    return FolioTaskOut(
        id=item.id,
        text=item.text,
        done=item.done,
        due=item.due_date,
        bucket=task.bucket,
        node=_ref(task.node),
        url=node_link(task.node),
        updated_at=item.updated_at,
    )


async def _reader(db: Db, principal: CurrentPrincipal) -> None:
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()


@router.get("/me/tasks", response_model=FolioTasksOut)
async def my_tasks(
    principal: CurrentPrincipal, db: Db, status: Literal["open", "done", "all"] = "open"
) -> FolioTasksOut:
    """Action items assigned to you in documents you can see, by due date; each says
    whether it is overdue, due today, upcoming or has no date."""
    await _reader(db, principal)
    return FolioTasksOut(
        items=[_out(t) for t in await actions.my_tasks(db, principal.user, status)]
    )


@router.patch("/action-items/{item_id}", response_model=FolioTaskOut)
async def check_off(
    item_id: uuid.UUID, body: ActionItemPatch, principal: CurrentPrincipal, db: Db
) -> FolioTaskOut:
    """Check an item off (or back on). The document changes too, live if it is open."""
    await _reader(db, principal)
    return _out(await actions.set_done(db, principal.user, item_id, body.done))
