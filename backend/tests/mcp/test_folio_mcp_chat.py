"""ask_docs (Folio 4.5). Acceptance: an agent asks how to connect an agent and the answer
cites the right guide's section; a restricted page never reaches the model."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import Team, run_jobs
from tests.integration.folio_chat_helpers import docs, model
from tests.integration.folio_helpers import API
from tests.mcp.conftest import error_text, folio_mcp, payload

__all__ = ["docs", "model"]  # fixtures


async def test_acceptance_an_agent_asks_the_docs(
    client: AsyncClient, team: Team, docs: dict, model: list[dict]
) -> None:
    async with folio_mcp(client, team.agent) as folio:
        got = payload(await folio.call_tool("ask_docs", {"question": "¿Cómo conecto un agente?"}))
    assert got["answer"] == "Ve a Admin, Agentes [1]."
    cited = got["citations"][0]
    assert cited["n"] == 1 and cited["title"] == "Conecta un agente a Radicle"
    assert cited["section"] == "Conecta un agente" and cited["url"].endswith("#conecta-un-agente")
    assert cited["outdated"] is False


async def test_a_restricted_page_never_reaches_the_model(
    client: AsyncClient, db: AsyncSession, team: Team, docs: dict, model: list[dict]
) -> None:
    r = await client.put(
        f"{API}/nodes/{docs['guide']}/restrictions",
        headers=team.instance.headers,
        json={"view": [{"grantee_type": "user", "grantee": team.instance.handle}]},
    )
    assert r.status_code == 200
    await run_jobs(db)
    async with folio_mcp(client, team.agent) as folio:
        args = {"question": "¿Cómo conecto un agente con su token por MCP?"}
        got = payload(await folio.call_tool("ask_docs", args))
    assert all(c["title"] != "Conecta un agente a Radicle" for c in got["citations"])
    assert all("Admin, Agentes" not in sent["system"] for sent in model)


async def test_without_a_provider_it_says_what_to_set(
    client: AsyncClient, team: Team, docs: dict
) -> None:
    async with folio_mcp(client, team.agent) as folio:
        text = error_text(await folio.call_tool("ask_docs", {"question": "Hola"}))
    assert "AI provider" in text
