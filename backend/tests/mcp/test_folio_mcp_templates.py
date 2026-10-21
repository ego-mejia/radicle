"""Folio's template tools over MCP (Folio 3.1)."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload


async def test_an_agent_starts_a_build_spec(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, team, "eng")
    async with folio_mcp(client, team.agent) as folio:
        listed = payload(await folio.call_tool("list_templates"))
        spec = next(t for t in listed if t["doc_type_key"] == "build-spec")
        args = {"template": spec["id"], "space": "eng", "title": "Etapa 5: integraciones"}
        made = payload(await folio.call_tool("create_from_template", args))
        assert "## Entregables" in made["content_md"] and "@agent-backend" in made["content_md"]
        assert made["metadata"]["doc_type"] == "build-spec"
        args["template"] = "00000000-0000-0000-0000-000000000000"
        assert "not found" in error_text(await folio.call_tool("create_from_template", args))
