"""Docket's interface for other apps (Folio 4.1): always with the user's own access."""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.docket import public as docket
from radicle.platform.db.models import User
from radicle.platform.errors import Forbidden, ValidationFailed
from tests.conftest import Team, new_ticket
from tests.integration.test_restricted import restrict

API = "/api/v1"


async def _user(db: AsyncSession, handle: str) -> User:
    user = await db.scalar(select(User).where(User.handle == handle))
    assert user is not None
    return user


@pytest.fixture
async def tickets(client: AsyncClient, board: Team) -> Team:
    """PA-1 visible with a half-done checklist, assigned to luis; PA-2 restricted."""
    await new_ticket(
        client,
        board.admin,
        title="Visible",
        milestone="V1",
        assignee="luis",
        description_md="- [x] Diseño\n- [ ] Código",
    )
    await new_ticket(client, board.admin, title="Secreto")
    r = await client.post(
        f"{API}/projects/PA/security-levels",
        headers=board.admin.headers,
        json={"name": "Legal confidencial", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    assert (await restrict(client, board, "PA-2")).status_code == 200
    return board


async def test_get_tickets_hides_what_the_user_cannot_see(db: AsyncSession, tickets: Team) -> None:
    luis = await _user(db, "luis")
    found = await docket.get_tickets(db, ["pa-1", "PA-2", "ZZ-9", "nonsense"], luis)
    assert set(found) == {"PA-1", "PA-2", "ZZ-9", "NONSENSE"}
    one = found["PA-1"]
    assert one is not None and one.title == "Visible" and one.status_category == "todo"
    assert (one.assignee_handle, one.milestone, one.area) == ("luis", "V1", "Backend")
    assert (one.checklist_done, one.checklist_total) == (1, 2)
    assert found["PA-2"] is None and found["ZZ-9"] is None and found["NONSENSE"] is None
    olga = await _user(db, "olga")
    assert (await docket.get_tickets(db, ["PA-1"], olga)) == {"PA-1": None}
    by_id = await docket.get_tickets_by_id(db, [one.id], olga)
    assert by_id == {}
    assert list(await docket.get_tickets_by_id(db, [one.id], luis)) == [one.id]


async def test_search_uses_rql_and_access(db: AsyncSession, tickets: Team) -> None:
    luis = await _user(db, "luis")
    result = await docket.search(db, "project = PA", luis)
    assert [t.key for t in result.tickets] == ["PA-1"] and result.total == 1
    fernando = await _user(db, "fernando")
    assert (await docket.search(db, "project = PA", fernando)).total == 2
    with pytest.raises(ValidationFailed):
        await docket.search(db, "project = = PA", luis)


async def test_create_ticket_follows_docket_rules(db: AsyncSession, tickets: Team) -> None:
    luis = await _user(db, "luis")
    made = await docket.create_ticket(
        db, docket.NewTicket(project="pa", title="Desde Folio", area="Backend"), luis
    )
    assert made.key == "PA-3" and made.status_category == "todo"
    with pytest.raises(ValidationFailed, match="task, bug or draft"):
        await docket.create_ticket(db, docket.NewTicket(project="PA", title="x", type="epic"), luis)
    with pytest.raises(ValidationFailed):
        await docket.create_ticket(db, docket.NewTicket(project="PA", title="Sin área"), luis)
    vera = await _user(db, "vera")
    with pytest.raises(Forbidden):
        await docket.create_ticket(
            db, docket.NewTicket(project="PA", title="x", area="Backend"), vera
        )


async def test_get_milestone(db: AsyncSession, tickets: Team) -> None:
    luis = await _user(db, "luis")
    v1 = await docket.get_milestone(db, "pa", "v1", luis)
    assert v1 is not None and (v1.project, v1.name, v1.status) == ("PA", "V1", "open")
    assert await docket.get_milestone(db, "PA", "V9", luis) is None
    assert await docket.get_milestone(db, "PA", "V1", await _user(db, "olga")) is None
    assert await docket.get_milestone(db, "NOPE", "V1", luis) is None


async def test_projects_and_milestones_in_a_range(db: AsyncSession, board: Team) -> None:
    luis, olga = await _user(db, "luis"), await _user(db, "olga")
    assert await docket.get_project(db, " pa ", luis) == "PA"
    assert await docket.get_project(db, "PA", olga) is None
    assert await docket.get_project(db, "NOPE", luis) is None
    december = {"start": date(2026, 12, 1), "end": date(2026, 12, 15)}
    found = await docket.list_milestones(db, "pa", luis, **december)
    assert [(m.project, m.name, m.target_date) for m in found] == [("PA", "V1", date(2026, 12, 15))]
    november = {"start": date(2026, 11, 1), "end": date(2026, 11, 30)}
    assert await docket.list_milestones(db, "PA", luis, **november) == []
    assert await docket.list_milestones(db, "PA", olga, **december) == []
