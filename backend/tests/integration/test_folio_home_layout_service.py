"""The home layout service (Folio 3.2): validation, draft, publish, history, restore."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import home_layouts
from radicle.folio.services.home_layouts import DEFAULT
from radicle.platform.db.models import User
from radicle.platform.errors import Conflict, Forbidden, NotFound, ValidationFailed
from tests.conftest import Team


def _block(id: str, type: str, x: int = 0, w: int = 4, **config: object) -> dict:
    return {"id": id, "type": type, "x": x, "y": 0, "w": w, "h": 2, "config": config}


async def _user(db: AsyncSession, handle: str) -> User:
    found = await db.scalar(select(User).where(User.handle == handle))
    assert found is not None
    return found


async def test_the_default_layout_is_valid(db: AsyncSession) -> None:
    assert await home_layouts.validate(db, DEFAULT) == DEFAULT
    assert await home_layouts.active(db) == DEFAULT


@pytest.mark.parametrize(
    ("block", "field", "says"),
    [
        (_block("a", "nope"), "blocks[0].type", "Unknown block"),
        (_block("a", "spaces", x=10, w=4), "blocks[0]", "fit in the 12 columns"),
        (_block("a", "posts", limit=40), "blocks[0].config.limit", "between 1 and 12"),
        (_block("a", "query", rql="spaec = docs"), "blocks[0].config.rql", "Did you mean"),
        (_block("a", "query", rql=""), "blocks[0].config.rql", "Write the RQL"),
        (_block("a", "featured", node="not-an-id"), "blocks[0].config.node", "published"),
        (_block("a", "featured", node=str(uuid.uuid4())), "blocks[0].config.node", "published"),
        (_block("a", "text", markdown="x" * 6000), "blocks[0].config.markdown", "5000"),
        ({"id": "a", "type": "spaces"}, "blocks[0]", "whole numbers"),
    ],
)
async def test_validation_says_which_block(
    db: AsyncSession, block: dict, field: str, says: str
) -> None:
    with pytest.raises(ValidationFailed) as exc:
        await home_layouts.validate(db, {"blocks": [block]})
    assert any(e["field"] == field and says in e["message"] for e in exc.value.errors)


async def test_ids_rql_positions_and_normalized_configs(db: AsyncSession) -> None:
    bad = {"blocks": [_block("a", "spaces"), _block("a", "query", rql="space = = x")]}
    with pytest.raises(ValidationFailed) as exc:
        await home_layouts.validate(db, bad)
    errors = exc.value.errors
    assert any(e["field"] == "blocks[1].id" for e in errors)
    assert next(e for e in errors if e["field"] == "blocks[1].config.rql")["position"] == 8
    good = await home_layouts.validate(
        db, {"blocks": [_block("p", "posts", label="#Onboarding", space="AI-Tools", extra=1)]}
    )
    assert good["blocks"][0]["config"] == {
        "limit": 6,
        "title": "",
        "space": "ai-tools",
        "label": "onboarding",
        "kind": "posts",
    }
    with pytest.raises(ValidationFailed):
        await home_layouts.validate(db, {"blocks": "no"})


async def test_draft_publish_history_restore(db: AsyncSession, team: Team) -> None:
    admin = await _user(db, team.instance.handle)
    assert (await home_layouts.get_draft(db, admin)).saved is False
    with pytest.raises(Conflict):
        await home_layouts.publish(db, admin)
    one = {"blocks": [_block("s", "spaces", w=12)]}
    draft = await home_layouts.save_draft(db, admin, one)
    assert draft.saved and len(draft.layout["blocks"]) == 1
    await home_layouts.save_draft(db, admin, one)  # still one draft
    first = await home_layouts.publish(db, admin)
    assert first.is_active and (await home_layouts.active(db))["blocks"][0]["id"] == "s"
    await home_layouts.save_draft(db, admin, {"blocks": [_block("t", "text", markdown="Hola")]})
    second = await home_layouts.publish(db, admin)
    history = await home_layouts.history(db, admin)
    assert [h.id for h in history] == [second.id, first.id]
    assert [h.is_active for h in history] == [True, False]
    again = await home_layouts.restore(db, admin, first.id)
    assert again.layout == first.layout and again.is_active
    assert len(await home_layouts.history(db, admin)) == 3
    with pytest.raises(NotFound):
        await home_layouts.restore(db, admin, uuid.uuid4())


async def test_only_folio_admins(db: AsyncSession, team: Team) -> None:
    member = await _user(db, team.member.handle)
    for call in (
        home_layouts.get_draft(db, member),
        home_layouts.save_draft(db, member, DEFAULT),
        home_layouts.publish(db, member),
        home_layouts.history(db, member),
    ):
        with pytest.raises(Forbidden):
            await call
