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


VISUAL_CALLS = {
    "insert_visual": {"format": "svg", "code": "<svg/>", "title": "x", "description": "Un dibujo"},
    "insert_diagram": {"source": "flowchart LR; A-->B"},
    "insert_chart": {"kind": "bar", "data": [["Mes", "Abiertos"], ["Ene", 4]]},
    "insert_timeline": {"items": [{"title": "Lanzamiento"}]},
}

# Tools that take or return docs, each checked below; the rest never touch a page.
COVERED = {
    "get_space_tree",
    "search_docs",
    "query_docs",
    "get_page",
    "get_versions",
    "update_draft",
    "submit_for_publication",
    "list_comments",
    "add_comment",
    "resolve_comment",
    "list_my_tasks",
    "set_task_done",
    "watch",
    "get_feed",
    "append_to_live_doc",
    "query_database",
    "add_database_rows",
    "insert_visual",
    "insert_diagram",
    "insert_chart",
    "insert_timeline",
    "link_ticket",
    "unlink_ticket",
}
# whoami, spaces and the schema hold no page; create_page makes a new one, and
# list_my_submissions lists only the caller's own.
# Templates hold no page either; create_from_template makes a new one.
EXEMPT = {
    "whoami",
    "list_spaces",
    "get_metadata_schema",
    "create_page",
    "list_my_submissions",
    "list_templates",
    "create_from_template",
    "list_notifications",  # only your own, already filtered by each app's resolver
    "create_live_doc",
    "validate_visual",  # checks code it is sent; touches no page
    "get_docs_for_ticket",  # docs of a ticket you see; test_folio_mcp_tickets.py
}


async def test_every_folio_tool_is_covered(client: AsyncClient, team: Team) -> None:
    async with folio_mcp(client, team.agent) as folio:
        tools = {t.name for t in (await folio.list_tools()).tools}
    assert tools == COVERED | EXEMPT, "a new Folio tool needs a check for restricted pages"


async def test_restricted_pages_never_show_up(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    ids = await _docs(client, db, team)
    r = await client.post(
        f"{API}/nodes/{ids['secret']}/comments",
        headers=team.instance.headers,
        json={"body": "Solo para admins"},
    )
    hidden_thread = r.json()["id"]
    async with folio_mcp(client, team.agent) as folio:
        tree = payload(await folio.call_tool("get_space_tree", {"space": "docs"}))
        assert ids["secret"] not in str(tree)
        for mode in ("hybrid", "text"):
            args = {"query": "secreto", "mode": mode}
            assert payload(await folio.call_tool("search_docs", args)) == []
        assert payload(await folio.call_tool("query_docs", {"rql": 'title ~ "secreto"'})) == []
        writes = {
            "update_draft": {"content_md": "x"},
            "submit_for_publication": {"change_note": "x"},
            "add_comment": {"body": "x"},
            "append_to_live_doc": {"content_md": "x"},
            "add_database_rows": {"rows": [{"name": "x"}]},
            "link_ticket": {"key": "PA-1"},
            "unlink_ticket": {"key": "PA-1"},
            **VISUAL_CALLS,
        }
        for tool in ("get_page", "get_versions", "list_comments", "query_database", *writes):
            args = {"id": ids["secret"]} | writes.get(tool, {})
            text = error_text(await folio.call_tool(tool, args))
            assert "not found" in text.lower(), (tool, text)
        args = {"thread_id": hidden_thread}
        text = error_text(await folio.call_tool("resolve_comment", args))
        assert "not found" in text.lower()


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


async def test_every_tool_explains_missing_access(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    """Without a Folio grant each tool, reading or writing, says why instead of failing."""
    await _docs(client, db, team)
    i = team.instance.headers
    grants = (await client.get(f"{API}/admin/grants", headers=i)).json()["items"]
    for g in grants:
        await client.delete(f"{API}/admin/grants/{g['id']}", headers=i)
    some_id = "00000000-0000-0000-0000-000000000000"
    calls = {
        "list_spaces": {},
        "get_space_tree": {"space": "docs"},
        "search_docs": {"query": "agente"},
        "query_docs": {"rql": "space = docs"},
        "get_page": {"id": some_id},
        "get_metadata_schema": {},
        "get_versions": {"id": some_id},
        "create_page": {"space": "docs", "title": "x", "content_md": "x", "metadata": {}},
        "update_draft": {"id": some_id, "content_md": "x"},
        "submit_for_publication": {"id": some_id, "change_note": "x"},
        "list_my_submissions": {},
        "list_templates": {},
        "create_from_template": {"template": some_id, "space": "docs", "title": "x"},
        "list_comments": {"id": some_id},
        "add_comment": {"id": some_id, "body": "x"},
        "resolve_comment": {"thread_id": some_id},
        "query_database": {"id": some_id},
        "add_database_rows": {"id": some_id, "rows": [{"name": "x"}]},
        "validate_visual": {"format": "svg", "code": "<svg/>"},
        "link_ticket": {"id": some_id, "key": "PA-1"},
        "unlink_ticket": {"id": some_id, "key": "PA-1"},
        "get_docs_for_ticket": {"key": "PA-1"},
        **{tool: {"id": some_id} | args for tool, args in VISUAL_CALLS.items()},
    }
    async with folio_mcp(client, team.agent) as folio:
        for tool, args in calls.items():
            text = error_text(await folio.call_tool(tool, args))
            assert "no access to Folio" in text, (tool, text)
