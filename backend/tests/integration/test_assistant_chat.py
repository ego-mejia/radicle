"""Radi answers from the usage guide, written by the LLM when one is configured."""

import json

import httpx
import pytest
from httpx import AsyncClient

from radicle.api.assistant import chat_limiter
from radicle.services.assistant import llm
from tests.conftest import Team

API = "/api/v1"


def ask(text: str, language: str = "en") -> dict:
    return {"messages": [{"role": "user", "content": text}], "language": language}


@pytest.fixture(autouse=True)
def _fresh_limits() -> None:
    chat_limiter.reset()


async def test_without_an_llm_radi_answers_from_the_guide(client: AsyncClient, board: Team) -> None:
    r = await client.post(
        f"{API}/assistant/chat",
        headers=board.member.headers,
        json=ask("How do I create a project?"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "guide" and body["sources"][0] == "Create a project"
    assert body["answer"].startswith("**Create a project**") and "Create project" in body["answer"]
    # The guide offers a ready-made tour, which waits for "Show me".
    assert body["tour"][0] == {
        "target": "nav.projects",
        "action": "click",
        "page": "/",
        "text": "Projects live here.",
    }
    assert body["autoplay"] is False

    r = await client.post(
        f"{API}/assistant/chat",
        headers=board.member.headers,
        json=ask("¿Cómo creo un proyecto?", "es"),
    )
    assert r.json()["sources"][0] == "Crear un proyecto"
    r = await client.post(
        f"{API}/assistant/chat", headers=board.member.headers, json=ask("zzz qqq")
    )
    assert r.json()["sources"] == [] and "could not find" in r.json()["answer"]


async def test_with_an_llm_it_writes_from_the_guide(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "Go to **Projects**."}]}
        )

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(handler))
    await client.put(
        f"{API}/admin/assistant",
        headers=board.instance.headers,
        json={"provider": "anthropic", "api_key": "k"},
    )
    conversation = {
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "how do I create a project?"},
        ],
        "language": "es",
    }
    r = await client.post(f"{API}/assistant/chat", headers=board.member.headers, json=conversation)
    assert r.json()["answer"] == "Go to **Projects**." and r.json()["mode"] == "llm"
    assert "Crear un proyecto" in r.json()["sources"]
    # No walkthrough from the model: the guide's tour is offered (not autoplayed).
    assert r.json()["tour"][0]["target"] == "nav.projects" and r.json()["autoplay"] is False
    system = sent[0]["system"]
    assert "Reply in Spanish" in system and "## Crear un proyecto" in system
    assert [m["role"] for m in sent[0]["messages"]] == ["user", "assistant", "user"]


async def test_llm_down_falls_back_to_the_guide(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        llm, "transport", httpx.MockTransport(lambda r: httpx.Response(500, text="boom"))
    )
    await client.put(
        f"{API}/admin/assistant",
        headers=board.instance.headers,
        json={"provider": "anthropic", "api_key": "k"},
    )
    member = await client.post(
        f"{API}/assistant/chat", headers=board.member.headers, json=ask("create a project")
    )
    assert member.json()["mode"] == "guide"
    assert (
        member.json()["notice"]
        == "My AI is not available right now, so here is what the guide says."
    )
    admin = await client.post(
        f"{API}/assistant/chat", headers=board.instance.headers, json=ask("create a project")
    )
    assert "answered 500" in admin.json()["notice"]


async def test_validation_auth_and_rate_limit(client: AsyncClient, board: Team) -> None:
    h = board.member.headers
    bad = {"messages": [{"role": "assistant", "content": "hello"}]}
    assert (await client.post(f"{API}/assistant/chat", headers=h, json=bad)).status_code == 422
    assert (
        await client.post(f"{API}/assistant/chat", headers=h, json={"messages": []})
    ).status_code == 422
    anonymous = AsyncClient(transport=client._transport, base_url="http://test")
    assert (await anonymous.post(f"{API}/assistant/chat", json=ask("hi"))).status_code == 401
    codes = [
        (await client.post(f"{API}/assistant/chat", headers=h, json=ask("board"))).status_code
        for _ in range(21)
    ]
    assert codes[:20] == [200] * 20 and codes[20] == 429


async def test_the_model_can_walk_the_user_through_the_screen(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[dict] = []

    def openai(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        steps = [
            {"target": "projects.create", "action": "click", "text": "Abre el diálogo"},
            {"target": "project-form.submit", "action": "click", "text": "Guárdalo"},
            {"target": "made.up", "action": "click", "text": "?"},
        ]
        call = {"function": {"name": "show_me", "arguments": json.dumps({"steps": steps})}}
        return httpx.Response(
            200, json={"choices": [{"message": {"content": None, "tool_calls": [call]}}]}
        )

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(openai))
    await client.put(
        f"{API}/admin/assistant",
        headers=board.instance.headers,
        json={"provider": "openai", "api_key": "k"},
    )
    r = await client.post(
        f"{API}/assistant/chat", headers=board.member.headers, json=ask("crea un proyecto", "es")
    )
    body = r.json()
    assert body["answer"] == "Te muestro." and body["autoplay"] is True
    assert [(s["target"], s["action"]) for s in body["tour"]] == [
        ("projects.create", "click"),
        ("project-form.submit", "point"),
    ]
    tool = sent[0]["tools"][0]["function"]
    assert tool["name"] == "show_me" and "projects.create" in sent[0]["messages"][0]["content"]


async def test_anthropic_tool_use_works_too(
    client: AsyncClient, board: Team, monkeypatch: pytest.MonkeyPatch
) -> None:
    def anthropic(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["tools"][0]["name"] == "show_me"
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "Follow me."},
                    {
                        "type": "tool_use",
                        "name": "show_me",
                        "input": {"steps": [{"target": "radi", "action": "point", "text": "Hi"}]},
                    },
                ]
            },
        )

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(anthropic))
    await client.put(
        f"{API}/admin/assistant",
        headers=board.instance.headers,
        json={"provider": "anthropic", "api_key": "k"},
    )
    r = await client.post(
        f"{API}/assistant/chat", headers=board.member.headers, json=ask("hello radi")
    )
    assert r.json()["answer"] == "Follow me." and r.json()["tour"][0]["target"] == "radi"
