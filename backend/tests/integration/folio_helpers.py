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
