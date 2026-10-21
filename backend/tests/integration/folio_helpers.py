"""Shared steps for Folio API tests."""

from httpx import AsyncClient

from tests.conftest import Team

API = "/api/v1/folio"
METADATA = {
    "description": "Cómo conectar un agente a Radicle por MCP, paso a paso y con el token.",
    "doc_type": "how-to",
    "labels": ["mcp", "#Agentes"],
    "owner": "@fernando",
    "audiences": ["everyone"],
    "language": "es",
}


async def publish(client: AsyncClient, team: Team, node_id: str, md: str = "Hola") -> dict:
    """Write and publish a page as the instance admin, so readers can see it."""
    i = team.instance.headers
    r = await client.put(
        f"{API}/nodes/{node_id}/draft", headers=i, json={"content_md": md, "metadata": METADATA}
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/nodes/{node_id}/publish", headers=i, json={})
    assert r.status_code == 201, r.text
    return r.json()


async def agent_can_write(client: AsyncClient, team: Team, space: str) -> None:
    """Make the team's agent a Folio creator with create in `space`."""
    i = team.instance.headers
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": team.agent.handle, "role": "creator"},
    )
    assert r.status_code == 201, r.text
    grants = (await client.get(f"{API}/spaces/{space}/grants", headers=i)).json()["grants"]
    grants.append(
        {"grantee_type": "user", "grantee": team.agent.handle, "permissions": ["view", "create"]}
    )
    r = await client.put(f"{API}/spaces/{space}/grants", headers=i, json={"grants": grants})
    assert r.status_code == 200, r.text


async def agent_submits(client: AsyncClient, team: Team, space: str, title: str) -> dict:
    """The agent writes a new page and publishes it, which sends it for approval."""
    a = team.agent.headers
    node = await client.post(
        f"{API}/nodes", headers=a, json={"space": space, "kind": "page", "title": title}
    )
    assert node.status_code == 201, node.text
    nid = node.json()["id"]
    r = await client.put(
        f"{API}/nodes/{nid}/draft",
        headers=a,
        json={"content_md": "# Cambios", "metadata": METADATA},
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/nodes/{nid}/publish", headers=a, json={"change_note": "Semana"})
    assert r.status_code == 202, r.text
    return r.json()
