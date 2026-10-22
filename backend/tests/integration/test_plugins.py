"""Plugins (ADR 0043): instance admins install a manifest, turn it off and on, update it
and remove it; apps read what enabled plugins bring to their hooks."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.services import plugins
from tests.conftest import Team
from tests.integration.plugin_helpers import manifest, test_hook

__all__ = ["test_hook"]
API = "/api/v1/admin/plugins"


async def test_install_toggle_update_remove(
    client: AsyncClient, db: AsyncSession, team: Team, test_hook: None
) -> None:
    i = team.instance.headers
    r = await client.post(API, headers=i, json={"manifest": manifest()})
    assert r.status_code == 201, r.text
    assert r.json()["enabled"] and r.json()["hooks"] == ["test.widgets"]
    found = await plugins.contributions(db, "test.widgets")
    assert [(c.plugin, c.value) for c in found] == [("acme.widgets", ["a", "b"])]

    r = await client.patch(f"{API}/acme.widgets", headers=i, json={"enabled": False})
    assert r.json()["enabled"] is False
    assert await plugins.contributions(db, "test.widgets") == []
    await client.patch(f"{API}/acme.widgets", headers=i, json={"enabled": False})  # no change

    update = manifest(version="1.1.0", hooks={"test.widgets": ["c"]})
    r = await client.post(API, headers=i, json={"manifest": update})
    assert r.status_code == 201 and r.json()["version"] == "1.1.0"
    assert r.json()["enabled"] is False  # updating keeps it off
    listed = (await client.get(API, headers=i)).json()
    assert [p["key"] for p in listed["items"]] == ["acme.widgets"]
    assert "test.widgets" in listed["hooks"]
    assert (await client.delete(f"{API}/acme.widgets", headers=i)).status_code == 204
    assert (await client.delete(f"{API}/acme.widgets", headers=i)).status_code == 404


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("nope", "JSON object"),
        (manifest(key="Acme Widgets"), "lowercase"),
        (manifest(key=""), "key is required"),
        (manifest(version="1.0"), "semver"),
        (manifest(name="x" * 81), "name"),
        (manifest(description=3), "description"),
        (manifest(hooks={}), "at least one hook"),
        (manifest(hooks={"docket.board": []}), "Unknown hook docket.board"),
        (manifest(hooks={"test.widgets": "a"}), "list of names"),
    ],
)
async def test_bad_manifests_say_what_to_fix(
    client: AsyncClient, team: Team, test_hook: None, body: object, message: str
) -> None:
    r = await client.post(API, headers=team.instance.headers, json={"manifest": body})
    if body == "nope":
        assert r.status_code == 422
        return
    assert r.status_code == 422 and message in r.json()["detail"], r.text


async def test_only_instance_admins(client: AsyncClient, team: Team, test_hook: None) -> None:
    for actor in (team.admin, team.member, team.agent):
        h = actor.headers
        assert (await client.get(API, headers=h)).status_code == 403
        r = await client.post(API, headers=h, json={"manifest": manifest()})
        assert r.status_code == 403
    r = await client.patch(f"{API}/x", headers=team.instance.headers, json={"enabled": True})
    assert r.status_code == 404 and "lists the installed" in r.json()["detail"]
