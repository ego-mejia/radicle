"""Version history (Folio 1.3): list, read, compare and restore."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.test_folio_publish import METADATA

API = "/api/v1/folio"


@pytest.fixture
async def page(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Guía"}
    )
    return r.json()


async def _publish(client: AsyncClient, team: Team, page: dict, md: str, **metadata: object):
    i = team.instance.headers
    url = f"{API}/nodes/{page['id']}"
    r = await client.put(
        f"{url}/draft", headers=i, json={"content_md": md, "metadata": METADATA | metadata}
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{url}/publish", headers=i, json={"change_note": md[:20]})
    assert r.status_code == 201, r.text
    return r.json()


async def test_publish_three_compare_and_restore_the_first(
    client: AsyncClient, team: Team, page: dict
) -> None:
    await _publish(client, team, page, "# Uno\n\nIgual\n\nViejo", title="Guía v1")
    await _publish(client, team, page, "# Uno\n\nIgual\n\nNuevo", title="Guía v2")
    await _publish(client, team, page, "# Uno\n\nIgual\n\nNuevo\n\nMás", labels=["otro"])
    url = f"{API}/nodes/{page['id']}"
    reader = team.member.headers

    history = (await client.get(f"{url}/versions", headers=reader)).json()["items"]
    assert [v["number"] for v in history] == [3, 2, 1]
    assert history[-1]["author"] == "fernando" and history[-1]["change_note"].startswith("# Uno")

    one = (await client.get(f"{url}/versions/1", headers=reader)).json()
    assert one["content_md"] == "# Uno\n\nIgual\n\nViejo\n" and one["title"] == "Guía v1"

    d = (await client.get(f"{url}/diff", params={"from": 1, "to": 3}, headers=reader)).json()
    assert [(b["op"], b["block"].get("content", [{}])[0].get("text")) for b in d["blocks"]] == [
        ("equal", "Uno"),
        ("equal", "Igual"),
        ("removed", "Viejo"),
        ("added", "Nuevo"),
        ("added", "Más"),
    ]
    assert d["title"] == {"field": "title", "before": "Guía v1", "after": "Guía v2"}
    assert {"field": "labels", "before": ["mcp", "agentes"], "after": ["otro"]} in d["metadata"]

    r = await client.post(f"{url}/versions/1/restore", headers=team.instance.headers, json={})
    assert r.status_code == 201, r.text
    four = r.json()
    assert (four["number"], four["restored_from"]) == (4, 1)
    assert four["change_note"] == "Restored version 1"
    node = (await client.get(url, headers=reader)).json()
    assert node["version"] == 4 and node["title"] == "Guía v1"
    draft = (await client.get(f"{url}/draft", headers=team.instance.headers)).json()
    assert draft["content_md"] == one["content_md"]
    # The draft follows the restore, so publishing again needs no confirmation.
    assert (
        await client.post(f"{url}/publish", headers=team.instance.headers, json={})
    ).status_code == 201


async def test_actionable_errors(client: AsyncClient, team: Team, page: dict) -> None:
    await _publish(client, team, page, "solo")
    url = f"{API}/nodes/{page['id']}"
    i = team.instance.headers
    r = await client.get(f"{url}/versions/9", headers=i)
    assert r.status_code == 404 and "lists them" in r.json()["detail"]
    assert (
        await client.get(f"{url}/diff", params={"from": 1, "to": 9}, headers=i)
    ).status_code == 404
    assert (
        await client.get(f"{url}/diff", params={"from": 0, "to": 1}, headers=i)
    ).status_code == 422
    r = await client.post(f"{url}/versions/1/restore", headers=i, json={})
    assert r.status_code == 422 and "already the published one" in r.json()["detail"]


async def test_readers_read_history_but_do_not_restore(
    client: AsyncClient, team: Team, page: dict
) -> None:
    await _publish(client, team, page, "uno")
    await _publish(client, team, page, "dos")
    url = f"{API}/nodes/{page['id']}"
    r = await client.post(f"{url}/versions/1/restore", headers=team.member.headers, json={})
    assert r.status_code == 403
    await client.post(
        f"{API}/admin/grants",
        headers=team.instance.headers,
        json={"grantee_type": "user", "grantee": "agent-backend", "role": "creator"},
    )
    r = await client.post(f"{url}/versions/1/restore", headers=team.agent.headers, json={})
    assert r.status_code == 403
