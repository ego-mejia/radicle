"""Generic authorization (ADR 0035): platform routes to each app's provider and fails
closed; Docket's provider answers like its own routes; group lookups cache for 60 s."""

from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import ColumnElement, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket.db.models import Project, Ticket
from radicle.platform import authz
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, NotFound
from radicle.platform.services import groups
from tests.conftest import Team, new_ticket, patch_ticket


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


async def _project(db: AsyncSession) -> Project:
    project = await db.scalar(select(Project).where(Project.key == "PA"))
    assert project is not None
    return project


async def test_docket_provider_follows_the_matrix(db: AsyncSession, board: Team) -> None:
    project = await _project(db)
    member, viewer, outsider = [
        await _user(db, h) for h in (board.member.handle, board.viewer.handle, "olga")
    ]
    assert (await authz.authorize(db, member, "docket", "ticket.create", project)).allowed
    assert (await authz.authorize(db, viewer, "docket", None, project)).allowed

    denied = await authz.authorize(db, viewer, "docket", "ticket.create", project)
    assert not denied.allowed and denied.status == 403
    assert "ticket.create" in denied.reason
    with pytest.raises(Forbidden):
        denied.raise_if_denied()

    hidden = await authz.authorize(db, outsider, "docket", None, project)
    assert not hidden.allowed and hidden.status == 404
    with pytest.raises(NotFound):
        hidden.raise_if_denied()


async def test_docket_provider_hides_restricted_tickets(
    client: AsyncClient, db: AsyncSession, board: Team
) -> None:
    r = await client.post(
        "/api/v1/projects/PA/security-levels",
        headers=board.admin.headers,
        json={"name": "Legal", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    key = (await new_ticket(client, board.admin, title="Secret"))["key"]
    r = await patch_ticket(client, board.admin, key, security_level="Legal")
    assert r.status_code == 200, r.text
    ticket = await db.scalar(select(Ticket).where(Ticket.number == int(key.split("-")[1])))
    member = await _user(db, board.member.handle)

    decision = await authz.authorize(db, member, "docket", None, ticket)
    assert not decision.allowed and decision.status == 404 and key in decision.reason
    visible = await db.scalars(select(Ticket.id).where(authz.visible(member, "docket", Ticket)))
    assert ticket.id not in set(visible)
    admin = await _user(db, "ana")
    assert (await authz.authorize(db, admin, "docket", None, ticket)).allowed


async def test_unknown_app_and_resource_fail_closed(db: AsyncSession, board: Team) -> None:
    admin = await _user(db, "ana")
    unknown = await authz.authorize(db, admin, "nope", "anything")
    assert not unknown.allowed and unknown.status == 404
    assert "docket" in unknown.reason
    rows = await db.scalars(select(Ticket.id).where(authz.visible(admin, "nope", Ticket)))
    assert list(rows) == []
    weird = await authz.authorize(db, admin, "docket", None, "PA")
    assert not weird.allowed


class _Everyone:
    app = "test"

    async def check(self, db: AsyncSession, user: User, permission: str | None, resource: Any):  # type: ignore[no-untyped-def]
        return authz.Decision.allow() if permission == "read" else authz.Decision(False, "no")

    def visible_clause(self, user: User, model: Any) -> ColumnElement[bool]:
        return true()


@pytest.fixture
def test_provider() -> Iterator[None]:
    authz.register(_Everyone())
    yield
    authz.unregister("test")


async def test_a_provider_registers_and_answers(
    db: AsyncSession, board: Team, test_provider: None
) -> None:
    admin = await _user(db, "ana")
    assert "test" in authz.apps()
    assert (await authz.authorize(db, admin, "test", "read")).allowed
    assert not (await authz.authorize(db, admin, "test", "write")).allowed


async def test_group_ids_cache_for_sixty_seconds(
    client: AsyncClient, db: AsyncSession, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [1000.0]
    monkeypatch.setattr(groups, "_now", lambda: now[0])
    monkeypatch.setattr(groups, "_cache", {})
    headers = board.instance.headers
    r = await client.post("/api/v1/groups", headers=headers, json={"name": "equipo-docs"})
    assert r.status_code == 201, r.text
    group = {(await groups.get_group(db, "equipo-docs")).id}
    r = await client.put("/api/v1/groups/equipo-docs/members/luis", headers=headers)
    assert r.status_code == 200, r.text

    luis = await _user(db, "luis")
    assert await groups.group_ids(db, luis) == group
    r = await client.delete("/api/v1/groups/equipo-docs/members/luis", headers=headers)
    assert r.status_code == 200, r.text

    now[0] += 59
    assert await groups.group_ids(db, luis) == group
    now[0] += 2
    assert await groups.group_ids(db, luis) == frozenset()
