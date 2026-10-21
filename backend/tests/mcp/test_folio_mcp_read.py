"""Folio's MCP read tools (Folio 1.7): an agent finds docs, reads them in Markdown and
learns what publishing needs; restricted pages never show up through any tool."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_helpers import API, publish
from tests.mcp.conftest import error_text, folio_mcp, payload

GUIDE = "Intro.\n\n# Conecta un agente\n\nCrea el agente en Admin y usa su token por MCP.\n"


async def _docs(client: AsyncClient, db: AsyncSession, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    made = {}
    for title in ("Conecta un agente", "Plan secreto"):
        r = await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
        )
        made[title] = r.json()["id"]
        await publish(client, team, made[title], md=GUIDE if "agente" in title else "Secreto.")
    r = await client.put(
        f"{API}/nodes/{made['Plan secreto']}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200, r.text
    await run_jobs(db)
    return {"guide": made["Conecta un agente"], "secret": made["Plan secreto"]}


async def test_an_agent_reads_docs(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    ids = await _docs(client, db, team)
    async with folio_mcp(client, team.agent) as folio:
        me = payload(await folio.call_tool("whoami"))
        assert me["spaces"] == [{"key": "docs", "permissions": ["view"]}]
        spaces = payload(await folio.call_tool("list_spaces"))
        assert [s["key"] for s in spaces] == ["docs"]
        tree = payload(await folio.call_tool("get_space_tree", {"space": "docs"}))
        assert [n["title"] for n in tree] == ["Conecta un agente"]

        hits = payload(await folio.call_tool("search_docs", {"query": "cómo conecto un agente"}))
        assert hits[0]["node_id"] == ids["guide"] and hits[0]["section"] == ["Conecta un agente"]
        assert hits[0]["url"].endswith("#conecta-un-agente")
        found = payload(await folio.call_tool("query_docs", {"rql": "#mcp ORDER BY title"}))
        assert [d["id"] for d in found] == [ids["guide"]] and found[0]["doc_type"] == "how-to"

        page = payload(await folio.call_tool("get_page", {"id": ids["guide"]}))
        assert page["version"] == 1 and page["draft"] is False and page["path"] == []
        assert "# Conecta un agente" in page["content_md"] and page["metadata"]["owner"]
        history = payload(await folio.call_tool("get_versions", {"id": ids["guide"]}))
        assert [v["number"] for v in history] == [1]
        schema = payload(await folio.call_tool("get_metadata_schema"))
        assert "how-to" in [t["key"] for t in schema["doc_types"]]
        assert {f["name"] for f in schema["fields"]} >= {"description", "doc_type", "owner"}


# Tools that take or return docs, each checked below; the rest never touch a page.
COVERED = {"get_space_tree", "search_docs", "query_docs", "get_page", "get_versions"}
EXEMPT = {"whoami", "list_spaces", "get_metadata_schema"}


async def test_every_folio_tool_is_covered(client: AsyncClient, team: Team) -> None:
    async with folio_mcp(client, team.agent) as folio:
        tools = {t.name for t in (await folio.list_tools()).tools}
    assert tools == COVERED | EXEMPT, "a new Folio tool needs a check for restricted pages"


async def test_restricted_pages_never_show_up(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    ids = await _docs(client, db, team)
    async with folio_mcp(client, team.agent) as folio:
        tree = payload(await folio.call_tool("get_space_tree", {"space": "docs"}))
        assert ids["secret"] not in str(tree)
        for mode in ("hybrid", "text"):
            args = {"query": "secreto", "mode": mode}
            assert payload(await folio.call_tool("search_docs", args)) == []
        assert payload(await folio.call_tool("query_docs", {"rql": 'title ~ "secreto"'})) == []
        for tool in ("get_page", "get_versions"):
            text = error_text(await folio.call_tool(tool, {"id": ids["secret"]}))
            assert "404" in text or "not found" in text.lower()


async def test_errors_explain_what_works(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    await _docs(client, db, team)
    async with folio_mcp(client, team.agent) as folio:
        text = error_text(await folio.call_tool("query_docs", {"rql": "spaec = docs"}))
        assert "Did you mean 'space'" in text
        text = error_text(await folio.call_tool("search_docs", {"query": "x", "mode": "semantic"}))
        assert "AI provider" in text
        assert (
            "not found"
            in error_text(await folio.call_tool("get_space_tree", {"space": "nada"})).lower()
        )
