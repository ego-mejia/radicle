"""The docs chat over REST (Folio 4.5): the happy path with streaming, errors and who may
see what."""

import json

from httpx import AsyncClient

from tests.conftest import Team
from tests.integration.folio_chat_helpers import docs, model
from tests.integration.folio_helpers import API

__all__ = ["docs", "model"]  # fixtures


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


async def test_ask_streams_and_saves_the_answer(
    client: AsyncClient, team: Team, docs: dict, model: list[dict]
) -> None:
    m = team.member.headers
    assert (await client.get(f"{API}/chat/availability", headers=m)).json()["available"]
    r = await client.post(f"{API}/chat/sessions", headers=m, json={})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    r = await client.post(
        f"{API}/chat/sessions/{sid}/messages",
        headers=m,
        json={"content": "¿Cómo conecto un agente?", "space": "docs"},
    )
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    got = events(r.text)
    assert [name for name, _ in got] == ["delta", "delta", "done"]
    answer = got[-1][1]["message"]
    assert answer["citations"][0]["node_id"] == docs["guide"]
    detail = (await client.get(f"{API}/chat/sessions/{sid}", headers=m)).json()
    assert detail["title"] == "¿Cómo conecto un agente?"
    assert [x["role"] for x in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["citations"][0]["anchor"] == "conecta-un-agente"
    listed = (await client.get(f"{API}/chat/sessions", headers=m)).json()["items"]
    assert [s["id"] for s in listed] == [sid]
    r = await client.post(
        f"{API}/chat/messages/{answer['id']}/feedback",
        headers=m,
        json={"value": "down", "note": "Falta el token"},
    )
    assert r.status_code == 200 and r.json()["feedback"] == "down"
    r = await client.get(f"{API}/admin/chat/unanswered", headers=team.instance.headers)
    assert r.json()["items"][0]["feedback_note"] == "Falta el token"


async def test_errors(client: AsyncClient, team: Team, docs: dict, model: list[dict]) -> None:
    m = team.member.headers
    sid = (await client.post(f"{API}/chat/sessions", headers=m, json={})).json()["id"]
    r = await client.post(f"{API}/chat/sessions/{sid}/messages", headers=m, json={"content": ""})
    assert r.status_code == 422
    unknown = "00000000-0000-0000-0000-000000000000"
    r = await client.post(
        f"{API}/chat/sessions/{unknown}/messages", headers=m, json={"content": "Hola"}
    )
    assert r.status_code == 404
    r = await client.post(
        f"{API}/chat/messages/{unknown}/feedback", headers=m, json={"value": "up"}
    )
    assert r.status_code == 404


async def test_without_a_provider_the_chat_is_off(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    m = team.member.headers
    off = (await client.get(f"{API}/chat/availability", headers=m)).json()
    assert off["available"] is False and "Admin, AI provider" in off["message"]
    sid = (await client.post(f"{API}/chat/sessions", headers=m, json={})).json()["id"]
    r = await client.post(
        f"{API}/chat/sessions/{sid}/messages", headers=m, json={"content": "Hola"}
    )
    assert r.status_code == 422 and r.json()["type"].endswith("no_chat_model")


async def test_permissions(client: AsyncClient, team: Team, docs: dict, model: list[dict]) -> None:
    m = team.member.headers
    sid = (await client.post(f"{API}/chat/sessions", headers=m, json={})).json()["id"]
    r = await client.post(
        f"{API}/chat/sessions/{sid}/messages",
        headers=m,
        json={"content": "¿Cómo conecto un agente?"},
    )
    answer = events(r.text)[-1][1]["message"]["id"]
    other = team.instance.headers
    assert (await client.get(f"{API}/chat/sessions/{sid}", headers=other)).status_code == 404
    r = await client.post(
        f"{API}/chat/sessions/{sid}/messages", headers=other, json={"content": "Hola"}
    )
    assert r.status_code == 404
    r = await client.post(
        f"{API}/chat/messages/{answer}/feedback", headers=other, json={"value": "up"}
    )
    assert r.status_code == 404
    assert (await client.get(f"{API}/chat/sessions", headers=other)).json()["items"] == []
    assert (await client.get(f"{API}/admin/chat/unanswered", headers=m)).status_code == 403
