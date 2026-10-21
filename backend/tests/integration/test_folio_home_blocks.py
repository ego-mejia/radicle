"""The home's blocks resolved for each reader (Folio 3.2)."""

import pytest
from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_chat_helpers import model
from tests.integration.folio_helpers import API, publish

__all__ = ["model"]  # fixture


def _block(id: str, type: str, y: int, **config: object) -> dict:
    return {"id": id, "type": type, "x": 0, "y": y, "w": 6, "h": 2, "config": config}


@pytest.fixture
async def docs(client: AsyncClient, team: Team) -> dict:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    await client.post(f"{API}/spaces", headers=i, json={"key": "vacio", "name": "Vacío"})
    made = {}
    for title, kind in (
        ("Post abierto", "blog_post"),
        ("Post secreto", "blog_post"),
        ("Guía", "page"),
    ):
        body = {"space": "docs", "kind": kind, "title": title}
        made[title] = (await client.post(f"{API}/nodes", headers=i, json=body)).json()["id"]
        await publish(client, team, made[title])
    r = await client.put(
        f"{API}/nodes/{made['Post secreto']}/restrictions",
        headers=i,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200, r.text
    return made


async def _publish_layout(client: AsyncClient, team: Team, *blocks: dict) -> None:
    i = team.instance.headers
    r = await client.put(f"{API}/admin/home/draft", headers=i, json={"blocks": list(blocks)})
    assert r.status_code == 200, r.text
    assert (await client.post(f"{API}/admin/home/publish", headers=i)).status_code == 201


async def _blocks(client: AsyncClient, team: Team, who: str = "member") -> dict[str, dict]:
    r = await client.get(f"{API}/home", headers=team.by_role(who).headers)
    assert r.status_code == 200, r.text
    return {b["id"]: b for b in r.json()["blocks"]}


def _titles(block: dict) -> list[str]:
    return [c["title"] for c in block["cards"]]


async def test_the_default_layout_until_one_is_published(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    blocks = await _blocks(client, team)
    assert set(blocks) >= {"featured", "latest", "spaces", "most-read"}
    assert "chat" not in blocks  # no AI provider: the docs chat is off
    assert "ai-tools" not in blocks  # no ai-tools space: nothing to show
    for block in blocks.values():
        assert "Post secreto" not in _titles(block)


async def test_each_block_with_what_the_reader_may_see(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    await _publish_layout(
        client,
        team,
        _block("pinned", "featured", 0, node=docs["Post secreto"]),
        _block("news", "announcement", 2, node=docs["Post abierto"]),
        _block("posts", "posts", 4, space="docs", kind="posts", limit=5),
        _block("all", "posts", 6, space="docs", kind="all", label="mcp", limit=5),
        _block("empty", "posts", 8, space="vacio"),
        _block("q", "query", 10, rql="kind = page", limit=3),
        _block("hot", "most_read", 12, limit=5),
        _block("you", "for_you", 14, limit=5),
        _block("sp", "spaces", 16),
        _block("txt", "text", 18, markdown="**Hola**"),
        _block("box", "search", 20),
        _block("chat", "chat", 22),
    )
    member = await _blocks(client, team)
    assert "pinned" not in member  # a restricted pinned post hides the block
    assert _titles(member["news"]) == ["Post abierto"]
    assert _titles(member["posts"]) == ["Post abierto"]
    assert set(_titles(member["all"])) == {"Post abierto", "Guía"}
    assert "empty" not in member and "chat" not in member
    assert _titles(member["q"]) == ["Guía"]
    assert "Post secreto" not in _titles(member["hot"])
    assert [s["key"] for s in member["sp"]["spaces"]] == ["docs", "vacio"]
    assert member["txt"]["markdown"] == "**Hola**" and "box" in member
    assert {"id", "type", "x", "y", "w", "h", "title"} <= set(member["q"])

    admin = await _blocks(client, team, "instance")
    assert _titles(admin["pinned"]) == ["Post secreto"]
    assert set(_titles(admin["posts"])) == {"Post abierto", "Post secreto"}


async def test_for_you_follows_what_you_watch(client: AsyncClient, team: Team, docs: dict) -> None:
    await _publish_layout(client, team, _block("you", "for_you", 0, limit=5))
    await client.put(f"{API}/watch/node/{docs['Guía']}", headers=team.member.headers)
    member = await _blocks(client, team)
    assert "Guía" in _titles(member["you"])


async def test_the_chat_block_shows_when_the_chat_is_on(
    client: AsyncClient, team: Team, docs: dict, model: list[dict]
) -> None:
    blocks = await _blocks(client, team)
    assert blocks["chat"]["type"] == "chat"
