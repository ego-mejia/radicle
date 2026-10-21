"""Folio's MCP prompts (Folio 4.7). Acceptance: an agent following weekly_changes_post
writes the week's post with a diagram and its tickets, and it waits for approval."""

import re

from httpx import AsyncClient

from radicle.docket.mcp.server import server as docket_server
from radicle.folio.mcp.server import server as folio_server
from tests.conftest import Team, new_ticket
from tests.integration.folio_helpers import API, METADATA, agent_can_write
from tests.mcp.conftest import folio_mcp, payload

ARGS = {
    "weekly_changes_post": {"space": "eng", "since": "v1.4", "repo": "radicle"},
    "document_module": {"space": "eng", "module": "backend/radicle/auth"},
    "build_spec_from_discussion": {
        "space": "eng",
        "title": "Fase 6",
        "discussion": "Ana: hagamos exportar a PDF.",
    },
}


async def test_each_prompt_is_listed_and_renders(client: AsyncClient, team: Team) -> None:
    async with folio_mcp(client, team.agent) as folio:
        listed = {p.name: p for p in (await folio.list_prompts()).prompts}
        assert set(listed) == set(ARGS)
        for name, args in ARGS.items():
            text = (await folio.get_prompt(name, args)).messages[0].content.text  # type: ignore[union-attr]
            assert "submit_for_publication" in text and '"eng"' in text
        weekly = await folio.get_prompt("weekly_changes_post", ARGS["weekly_changes_post"])
        text = weekly.messages[0].content.text  # type: ignore[union-attr]
        assert "v1.4..HEAD" in text and "radicle" in text
        spec = await folio.get_prompt(
            "build_spec_from_discussion", ARGS["build_spec_from_discussion"]
        )
        assert "exportar a PDF" in spec.messages[0].content.text  # type: ignore[union-attr]


async def test_prompts_name_only_real_tools() -> None:
    tools = {t.name for t in await folio_server.list_tools()}
    tools |= {t.name for t in await docket_server.list_tools()}
    for prompt in await folio_server.list_prompts():
        args = ARGS[prompt.name]
        text = (await folio_server.get_prompt(prompt.name, args)).messages[0].content.text  # type: ignore[union-attr]
        named = set(re.findall(r"`([a-z_]+)`", text))
        assert named, prompt.name
        assert named <= tools, f"{prompt.name} names unknown tools: {named - tools}"


async def test_acceptance_the_weekly_post_waits_for_approval(
    client: AsyncClient, board: Team
) -> None:
    await new_ticket(client, board.admin, title="Exportar a PDF")
    i = board.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, board, "eng")
    content = (
        "Esta semana llegó exportar a PDF.\n\n# Resumen\n\nUna semana corta.\n\n"
        "# Exportar\n\nEl nuevo exportador cierra :ticket[PA-1]."
    )
    async with folio_mcp(client, board.agent) as folio:
        args = {"space": "eng", "since": "v1.4"}
        assert (
            "insert_diagram"
            in (await folio.get_prompt("weekly_changes_post", args)).messages[0].content.text
        )  # type: ignore[union-attr]
        made = payload(
            await folio.call_tool(
                "create_page",
                {
                    "space": "eng",
                    "kind": "blog_post",
                    "title": "Cambios de la semana",
                    "content_md": content,
                    "metadata": METADATA | {"doc_type": "how-to"},
                },
            )
        )
        source = "flowchart LR; api-->export; export-->pdf"
        diagram = {"id": made["id"], "source": source, "after_heading": "Resumen"}
        assert not (await folio.call_tool("insert_diagram", diagram)).is_error
        link = {"id": made["id"], "key": "PA-1", "section": "exportar"}
        assert payload(await folio.call_tool("link_ticket", link))["ticket"]["key"] == "PA-1"
        sent = payload(
            await folio.call_tool(
                "submit_for_publication", {"id": made["id"], "change_note": "git log v1.4..HEAD"}
            )
        )
        assert sent["status"] == "pending"
        page = payload(await folio.call_tool("get_page", {"id": made["id"]}))
        assert "```mermaid" in page["content_md"] and ":ticket[PA-1]" in page["content_md"]
        docs = payload(await folio.call_tool("get_docs_for_ticket", {"key": "PA-1"}))
        assert [d["section"] for d in docs] == ["exportar"]
