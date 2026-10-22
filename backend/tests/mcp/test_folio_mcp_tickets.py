"""Folio's Docket tools (Folio 4.1): an agent links a doc's section to a ticket, finds the
ticket's docs and unlinks it; restricted tickets stay out of reach."""

from httpx import AsyncClient

from tests.conftest import Team, new_ticket
from tests.integration.folio_helpers import API, METADATA, agent_can_write, publish
from tests.integration.test_restricted import restrict
from tests.mcp.conftest import error_text, folio_mcp, payload


async def test_an_agent_links_finds_and_unlinks(client: AsyncClient, board: Team) -> None:
    await new_ticket(client, board.admin, title="Conectar agentes")
    await new_ticket(client, board.admin, title="SECRETO")
    r = await client.post(
        "/api/v1/projects/PA/security-levels",
        headers=board.admin.headers,
        json={"name": "Legal confidencial", "include_participants": False},
    )
    assert r.status_code == 201, r.text
    assert (await restrict(client, board, "PA-2")).status_code == 200
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, board, "eng")
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Guía"}
    )
    page = r.json()["id"]
    await publish(client, board, page, "# Conecta un agente\n\nVer PA-1.")

    async with folio_mcp(client, board.agent) as folio:
        args = {"id": page, "key": "pa-1", "section": "conecta-un-agente"}
        link = payload(await folio.call_tool("link_ticket", args))
        assert link["kind"] == "manual" and link["ticket"]["key"] == "PA-1"
        docs = payload(await folio.call_tool("get_docs_for_ticket", {"key": "PA-1"}))
        # Mentioned and linked on purpose: the doc shows once, with the section it links.
        assert [(d["kind"], d["section"]) for d in docs] == [("manual", "conecta-un-agente")]
        for tool, extra in (("link_ticket", {"id": page}), ("get_docs_for_ticket", {})):
            text = error_text(await folio.call_tool(tool, {"key": "PA-2", **extra}))
            assert "not found" in text and "SECRETO" not in text
        removed = payload(await folio.call_tool("unlink_ticket", {"id": page, "key": "PA-1"}))
        assert removed == {"removed": 2}
        assert payload(await folio.call_tool("get_docs_for_ticket", {"key": "PA-1"})) == []


async def test_an_agent_sends_a_build_spec_to_docket(client: AsyncClient, board: Team) -> None:
    from tests.integration.test_folio_build_spec import SPEC

    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, board, "eng")
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "eng", "kind": "page", "title": "Fase 4"}
    )
    page = r.json()["id"]
    r = await client.put(
        f"{API}/nodes/{page}/draft",
        headers=i,
        json={"content_md": SPEC, "metadata": METADATA | {"doc_type": "build-spec"}},
    )
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/nodes/{page}/publish", headers=i, json={})).is_success

    async with folio_mcp(client, board.agent) as folio:
        items = payload(await folio.call_tool("get_build_spec_items", {"id": page}))
        assert [(x["key"], x["linked"]) for x in items] == [("4.1", False), ("4.2", False)]
        args = {"id": page, "project": "PA", "area": "Backend"}
        dry = payload(await folio.call_tool("create_tickets_from_build_spec", args))
        assert dry["dry_run"] is True and [x["ticket"] for x in dry["items"]] == [None, None]
        r = await client.get(f"{API}/tickets/query", params={"rql": "project = PA"}, headers=i)
        assert r.json()["total"] == 0
        made = payload(
            await folio.call_tool("create_tickets_from_build_spec", args | {"dry_run": False})
        )
        assert [x["ticket"]["key"] for x in made["items"]] == ["PA-1", "PA-2"]
        again = payload(
            await folio.call_tool("create_tickets_from_build_spec", args | {"dry_run": False})
        )
        assert again["items"] == []
