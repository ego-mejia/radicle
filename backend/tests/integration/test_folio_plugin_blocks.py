"""Plugin blocks (Folio 5.7, ADR 0043). Acceptance: the example plugin adds a block; turned
off, it leaves the editor."""

import copy

import pytest
from httpx import AsyncClient

from radicle.folio.services import plugin_blocks
from tests.conftest import Team
from tests.integration.folio_helpers import API

ADMIN = "/api/v1/admin/plugins"


def _manifest(**block: object) -> dict:
    manifest = copy.deepcopy(plugin_blocks.example())
    manifest["key"] = "acme.blocks"
    manifest["hooks"]["folio.register_blocks"][0].update(block)
    return manifest


async def test_acceptance_the_example_adds_a_block(client: AsyncClient, team: Team) -> None:
    i, m = team.instance.headers, team.member.headers
    listed = (await client.get(ADMIN, headers=i)).json()
    assert "folio.register_blocks" in listed["hooks"]
    assert [(e["key"], e["installed"]) for e in listed["examples"]] == [
        ("radicle.countdown", False)
    ]
    r = await client.post(f"{ADMIN}/examples/radicle.countdown", headers=i)
    assert r.status_code == 201, r.text
    blocks = (await client.get(f"{API}/plugin-blocks", headers=m)).json()["items"]
    assert [b["id"] for b in blocks] == ["radicle.countdown/countdown"]
    countdown = blocks[0]
    assert [f["key"] for f in countdown["fields"]] == ["title", "date"]
    assert countdown["fields"][1] == {
        "key": "date",
        "label": "Fecha",
        "kind": "date",
        "required": True,
        "default": "",
        "options": [],
    }
    assert "window.radicle" in countdown["html"]
    await client.patch(f"{ADMIN}/radicle.countdown", headers=i, json={"enabled": False})
    assert (await client.get(f"{API}/plugin-blocks", headers=m)).json()["items"] == []
    assert (await client.get(ADMIN, headers=i)).json()["examples"][0]["installed"] is True
    r = await client.post(f"{ADMIN}/examples/nope", headers=i)
    assert r.status_code == 404 and "radicle.countdown" in r.json()["detail"]


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ({"type": "Count Down"}, "lowercase"),
        ({"name": ""}, "name is required"),
        ({"html": 3}, "the block's HTML"),
        ({"html": "<script>fetch('/x')</script>"}, "fetch()"),
        ({"html": '<img src="https://evil.example/x.png">'}, "won't load"),
        ({"fields": [{"key": "Bad Key", "label": "x"}]}, "lowercase"),
        ({"fields": [{"key": "a", "label": "x", "kind": "color"}]}, "kind is one of"),
        ({"fields": [{"key": "a", "label": "x", "kind": "select"}]}, "options"),
        ({"fields": [{"key": "a", "label": "x"}, {"key": "a", "label": "y"}]}, "own key"),
        ({"fields": "x"}, "at most 20 fields"),
    ],
)
async def test_bad_blocks_say_what_to_fix(
    client: AsyncClient, team: Team, block: dict, message: str
) -> None:
    r = await client.post(
        ADMIN, headers=team.instance.headers, json={"manifest": _manifest(**block)}
    )
    assert r.status_code == 422 and message in r.json()["detail"], r.text


async def test_the_hook_takes_a_list_of_distinct_blocks(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    manifest = _manifest()
    block = manifest["hooks"]["folio.register_blocks"][0]
    for value, message in (([], "1 to 20 blocks"), ([block, block], "own type"), (["x"], "is {")):
        manifest["hooks"]["folio.register_blocks"] = value
        r = await client.post(ADMIN, headers=i, json={"manifest": manifest})
        assert r.status_code == 422 and message in r.json()["detail"], r.text
    select = {"key": "size", "label": "Tamaño", "kind": "select", "options": ["S", "M"]}
    good = _manifest(fields=[select])
    assert (await client.post(ADMIN, headers=i, json={"manifest": good})).status_code == 201


async def test_readers_need_folio(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    grants = (await client.get(f"{API}/admin/grants", headers=i)).json()["items"]
    for g in grants:
        await client.delete(f"{API}/admin/grants/{g['id']}", headers=i)
    r = await client.get(f"{API}/plugin-blocks", headers=team.member.headers)
    assert r.status_code == 404 and "Folio" in r.json()["detail"]
