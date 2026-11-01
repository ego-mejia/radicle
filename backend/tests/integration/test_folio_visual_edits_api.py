"""Editing the visuals already in a draft over REST (ADR 0046): list, read, change, remove."""

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_helpers import API

SVG = '<svg viewBox="0 0 10 10"><rect fill="var(--rdc-accent)"/></svg>'


def _visual(title: str) -> dict[str, object]:
    attrs = {"format": "svg", "code": SVG, "title": title, "description": f"El cuadro {title}."}
    return {"type": "visual", "attrs": attrs}


async def _page(client: AsyncClient, team: Team) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": "Visuales"}
    )
    node = str(r.json()["id"])
    nested = {"type": "blockquote", "content": [_visual("B")]}
    doc = {"type": "doc", "content": [_visual("A"), nested, _visual("C")]}
    r = await client.put(f"{API}/nodes/{node}/draft", headers=i, json={"content_json": doc})
    assert r.status_code == 200, r.text
    return node


async def test_list_get_update_remove(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    node = await _page(client, team)
    r = await client.get(f"{API}/nodes/{node}/visuals", headers=i)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [(v["index"], v["title"]) for v in items] == [(0, "A"), (1, "B"), (2, "C")]
    assert items[0]["size"] == len(SVG) and "code" not in items[0]
    r = await client.get(f"{API}/nodes/{node}/visuals/1", headers=i)
    assert r.status_code == 200 and r.json()["code"] == SVG and r.json()["title"] == "B"
    html = '<button type="button">+</button><script>let n = 0;</script>'
    r = await client.patch(
        f"{API}/nodes/{node}/visuals/1", headers=i, json={"format": "html", "code": html}
    )
    assert r.status_code == 200, r.text
    assert r.json()["visuals"][1]["format"] == "html" and r.json()["visuals"][1]["title"] == "B"
    r = await client.get(f"{API}/nodes/{node}/draft", headers=i)
    quote = r.json()["content_json"]["content"][1]
    assert quote["content"][0]["attrs"]["code"] == html  # edited in place, still nested
    r = await client.delete(f"{API}/nodes/{node}/visuals/0", headers=i)
    assert r.status_code == 200, r.text
    assert [v["title"] for v in r.json()["visuals"]] == ["B", "C"]


async def test_errors(client: AsyncClient, team: Team) -> None:
    i = team.instance.headers
    node = await _page(client, team)
    r = await client.get(f"{API}/nodes/{node}/visuals/7", headers=i)
    assert r.status_code == 422 and "the draft has 3 visual(s)" in r.json()["detail"]
    r = await client.patch(
        f"{API}/nodes/{node}/visuals/0",
        headers=i,
        json={"code": '<svg><image href="https://x.io/a.png"/></svg>'},
    )
    assert r.status_code == 422 and "https://x.io/a.png" in r.json()["detail"]
    r = await client.get(f"{API}/nodes/{node}/visuals/0", headers=i)
    assert r.json()["code"] == SVG  # the refused change was not saved
    r = await client.delete(f"{API}/nodes/{node}/visuals/3", headers=i)
    assert r.status_code == 422


async def test_permissions(client: AsyncClient, team: Team) -> None:
    node = await _page(client, team)
    v = team.viewer.headers
    calls = (("GET", "visuals"), ("GET", "visuals/0"), ("PATCH", "visuals/0"))
    for method, path in (*calls, ("DELETE", "visuals/0")):
        body = {"title": "X"} if method == "PATCH" else None
        r = await client.request(method, f"{API}/nodes/{node}/{path}", headers=v, json=body)
        assert r.status_code in (403, 404), (method, path, r.text)
    client.cookies.clear()
    r = await client.get(f"{API}/nodes/{node}/visuals")
    assert r.status_code == 401
