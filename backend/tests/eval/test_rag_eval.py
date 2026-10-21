"""RAG evaluation (Folio 4.5): 50 questions over the test docs in rag_corpus.py.

- recall@8: the section that answers the question is among the 8 passages handed to the model.
- Citation accuracy: with a simulated model that cites the passage sharing the most words
  with the question, the answer's first citation points at that section. It measures the
  pipeline (ranking, numbering, citation mapping), not a real model's judgment.

The test fails under the thresholds in docs/folio/chat.md. Text search only: embeddings
would need a provider, which CI doesn't have.
"""

import json
import re

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import chat, retrieval
from radicle.platform.db.models import AiProvider, AiSettings, User
from radicle.platform.services import ai
from tests.conftest import Team, run_jobs
from tests.eval.rag_corpus import DOCS, QUESTIONS
from tests.integration.folio_helpers import API, METADATA

RECALL_AT_8 = 0.95
CITATION_ACCURACY = 0.80


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"\w{4,}", text.lower())}


def _extractive(request: httpx.Request) -> httpx.Response:
    """A stand-in model: cites the passage that shares the most words with the question."""
    body = json.loads(request.content)
    question = body["messages"][-1]["content"]
    passages = re.split(r"\n\n(?=\[\d+\] )", body["system"].split("Passages:\n\n")[1])
    scores = [len(_words(question) & _words(p)) for p in passages]
    best = scores.index(max(scores)) + 1
    events = [
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": f"Así [{best}]."}}
    ]
    return httpx.Response(200, content="".join(f"data: {json.dumps(e)}\n\n" for e in events))


@pytest.fixture
async def corpus(client: AsyncClient, db: AsyncSession, team: Team) -> None:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    for title, md in DOCS.items():
        r = await client.post(
            f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
        )
        nid = r.json()["id"]
        meta = METADATA | {"description": f"Documento interno del equipo: {title.lower()}."}
        await client.put(
            f"{API}/nodes/{nid}/draft", headers=i, json={"content_md": md, "metadata": meta}
        )
        r = await client.post(f"{API}/nodes/{nid}/publish", headers=i, json={})
        assert r.status_code == 201, r.text
    await run_jobs(db)


async def test_retrieval_and_citations_stay_above_the_thresholds(
    db: AsyncSession, team: Team, corpus: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert len(QUESTIONS) == 50
    member = await db.scalar(select(User).where(User.handle == team.member.handle))
    assert member is not None
    db.add(
        AiSettings(
            id=1,
            provider=AiProvider.anthropic,
            chat_model="claude-sonnet-5-5",
            base_url="https://api.anthropic.com",
            features={},
        )
    )
    monkeypatch.setattr(ai, "transport", httpx.MockTransport(_extractive))
    found, cited, misses = 0, 0, []
    for question, page, section in QUESTIONS:
        passages = await retrieval.retrieve(db, member, question)
        if any((p.title, p.section) == (page, section) for p in passages):
            found += 1
        else:
            misses.append(question)
        session = await chat.create_session(db, member)
        events = [e async for e in await chat.ask(db, member, session, question)]
        citations = events[-1].data["message"]["citations"]
        if citations and (citations[0]["title"], citations[0]["section"]) == (page, section):
            cited += 1
    recall, accuracy = found / len(QUESTIONS), cited / len(QUESTIONS)
    print(f"\nrecall@8 = {recall:.2f}, citation accuracy = {accuracy:.2f}")
    assert recall >= RECALL_AT_8, f"recall@8 {recall:.2f} < {RECALL_AT_8}; missed: {misses}"
    assert accuracy >= CITATION_ACCURACY, f"citation accuracy {accuracy:.2f} < {CITATION_ACCURACY}"
