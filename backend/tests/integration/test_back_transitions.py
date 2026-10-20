"""Default workflows let a ticket in review (or QA) go back to the first status, so a
card can be dragged back to To Do on the board."""

import pytest
from httpx import AsyncClient

from radicle.db.models import TicketType
from radicle.services.template_config import default_config
from tests.conftest import Team, new_ticket

API = "/api/v1"


async def move(client: AsyncClient, team: Team, key: str, to: str) -> None:
    r = await client.post(
        f"{API}/tickets/{key}/transitions", headers=team.member.headers, json={"to_status": to}
    )
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    ("fields", "path", "back"),
    [
        ({}, ["In Progress", "In Review"], "To Do"),
        ({"type": "bug"}, ["In Progress", "QA Verified"], "Reported"),
        ({"type": "draft", "area": None, "classification": "idea"}, ["In Review"], "New"),
    ],
)
async def test_back_to_the_first_status(
    client: AsyncClient, board: Team, fields: dict, path: list[str], back: str
) -> None:
    key = (await new_ticket(client, board.member, **fields))["key"]
    for status in path:
        await move(client, board, key, status)
    options = (
        await client.get(f"{API}/tickets/{key}/transitions", headers=board.member.headers)
    ).json()
    assert back in {o["to_status"] for o in options}
    await move(client, board, key, back)
    ticket = (await client.get(f"{API}/tickets/{key}", headers=board.member.headers)).json()
    assert ticket["status"]["name"] == back


async def test_the_default_template_has_them(client: AsyncClient, board: Team) -> None:
    templates = (await client.get(f"{API}/templates", headers=board.instance.headers)).json()
    default = next(t for t in templates["items"] if t["name"] == "Radicle default")
    detail = (
        await client.get(f"{API}/templates/{default['id']}", headers=board.instance.headers)
    ).json()
    refs = {
        kind: {t["ref"] for t in wf["transitions"]}
        for kind, wf in detail["config"]["workflows"].items()
    }
    assert "back_to_to_do" in refs["task"]
    assert "back_to_reported" in refs["bug"]
    assert "back_to_new" in refs["draft"]
    # The code fallback matches what the migration wrote.
    fallback = default_config().workflows
    for kind in TicketType:
        assert {t.ref for t in fallback[kind].transitions} == refs[kind.value]
