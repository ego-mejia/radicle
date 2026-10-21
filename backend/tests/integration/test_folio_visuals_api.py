"""Visuals over REST (Folio 3.3 and 3.4): the check, and adding a block to a draft."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API, publish

SVG = '<svg viewBox="0 0 10 10"><rect fill="var(--rdc-accent)"/></svg>'
VISUAL = {
    "type": "visual",
    "attrs": {
        "format": "svg",
        "code": SVG,
        "title": "Cuadro",
        "description": "Un cuadro en el color de acento.",
    },
}


async def _page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Visuales"}
    )
    node = str(r.json()["id"])
    await publish(client, team, node, md="# Uno\n\nA\n\n## Uno.1\n\nB\n\n# Dos\n\nC\n")
    return node


async def test_check_and_add(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    body = {
        "format": "svg",
        "code": SVG,
        "title": "Cuadro",
        "description": "Un cuadro en el color de acento.",
    }
    r = await client.post(f"{API}/visuals/check", headers=team.member.headers, json=body)
    assert r.status_code == 200, r.text
    assert r.json() == {"valid": True, "problems": [], "warnings": []}
    node = await _page(client, team)
    r = await client.post(
        f"{API}/nodes/{node}/blocks", headers=i, json={"block": VISUAL, "after_heading": "# Uno"}
    )
    assert r.status_code == 200, r.text
    md = r.json()["content_md"]
    assert md.index("## Uno.1") < md.index("```visual") < md.index("# Dos")  # end of section
    r = await client.post(
        f"{API}/nodes/{node}/blocks",
        headers=i,
        json={"block": {"type": "formula", "attrs": {"latex": "e=mc^2"}}},
    )
    assert r.json()["content_md"].rstrip().endswith("e=mc^2\n```")


async def test_errors(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    node = await _page(client, team)
    bad = {
        **VISUAL,
        "attrs": {**VISUAL["attrs"], "code": '<svg><image href="https://x.io/a.png"/></svg>'},
    }
    r = await client.post(f"{API}/nodes/{node}/blocks", headers=i, json={"block": bad})
    assert r.status_code == 422 and "https://x.io/a.png" in r.json()["detail"]
    r = await client.post(
        f"{API}/nodes/{node}/blocks", headers=i, json={"block": {"type": "chart", "attrs": {}}}
    )
    assert r.status_code == 422 and "kind" in r.text
    r = await client.post(f"{API}/visuals/check", headers=i, json={"format": "png", "code": "x"})
    assert r.status_code == 422
    # A visual without its title stays in the draft: it doesn't publish.
    untitled = {"type": "doc", "content": [{**VISUAL, "attrs": {**VISUAL["attrs"], "title": None}}]}
    r = await client.put(f"{API}/nodes/{node}/draft", headers=i, json={"content_json": untitled})
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/nodes/{node}/publish", headers=i, json={})
    assert r.status_code == 422 and "Give every visual a title" in r.json()["detail"]


async def test_permissions(client: AsyncClient, team: Team) -> None:
    node = await _page(client, team)
    # A reader may view the page but not change its draft.
    r = await client.post(
        f"{API}/nodes/{node}/blocks", headers=team.viewer.headers, json={"block": VISUAL}
    )
    assert r.status_code in (403, 404), r.text
    client.cookies.clear()
    r = await client.post(f"{API}/visuals/check", json={"format": "svg", "code": SVG})
    assert r.status_code == 401
