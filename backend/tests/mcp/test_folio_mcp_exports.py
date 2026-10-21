"""export_page over MCP (Folio 5.2)."""

import pytest
from httpx import AsyncClient

from radicle.folio.mcp import exports as exports_mcp
from tests.conftest import Team
from tests.integration.folio_helpers import API, agent_can_write, publish
from tests.mcp.conftest import error_text, folio_mcp, payload


async def _guide(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "guias", "name": "Guías"})
    body = {"space": "guias", "kind": "page", "title": "Conectar un agente"}
    page = (await client.post(f"{API}/nodes", headers=i, json=body)).json()
    await publish(client, team, page["id"], "# Paso 1\n\nPide el token.")
    return str(page["id"])


async def test_markdown_now_and_a_pdf_to_download(
    client: AsyncClient, team: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exports_mcp, "WAIT_SECONDS", 0)  # no worker in tests
    page = await _guide(client, team)
    await agent_can_write(client, team, "guias")
    grants = (await client.get(f"{API}/spaces/guias/grants", headers=team.instance.headers)).json()[
        "grants"
    ]
    for g in grants:
        if g.get("grantee") == team.agent.handle:
            g["permissions"].append("export")
    r = await client.put(
        f"{API}/spaces/guias/grants", headers=team.instance.headers, json={"grants": grants}
    )
    assert r.status_code == 200, r.text
    async with folio_mcp(client, team.agent) as folio:
        md = payload(await folio.call_tool("export_page", {"id": page}))
        assert md["version"] == 1 and "# Paso 1" in md["content_md"]
        pdf = payload(await folio.call_tool("export_page", {"id": page, "format": "pdf"}))
        assert pdf["status"] == "queued" and pdf["export_id"]


async def test_without_the_export_permission(client: AsyncClient, team: Team) -> None:
    page = await _guide(client, team)
    async with folio_mcp(client, team.agent) as folio:
        text = error_text(await folio.call_tool("export_page", {"id": page, "format": "pdf"}))
        assert "export permission" in text
