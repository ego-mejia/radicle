"""Folio's automation (Folio 5.6). Acceptance: the expiry rule posts on a channel when a
page turns Outdated."""

import json
import uuid
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.docket_links import FolioTicketLink
from radicle.folio.db.models import FolioNode, FolioNodeLabel
from radicle.folio.services import quality
from radicle.platform.db.models import AutomationRun, IntegrationKind, User
from radicle.platform.services import automation, integrations, safe_fetch
from radicle.platform.services.integrations import IntegrationData, Route
from tests.conftest import Clock, Team, run_jobs
from tests.integration.folio_helpers import API, publish


@pytest.fixture
def slack(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    posted: list[dict[str, Any]] = []

    def answer(request: httpx.Request) -> httpx.Response:
        posted.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    async def resolve(host: str) -> list[str]:
        return ["54.230.1.1"]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(answer))
    return posted


async def _admin(db: AsyncSession, team: Team) -> User:
    user = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert user is not None
    return user


async def _page(client: AsyncClient, team: Team, title: str) -> str:
    i = team.instance.headers
    await client.post(f"{API}/spaces", headers=i, json={"key": "docs", "name": "Docs"})
    r = await client.post(
        f"{API}/nodes", headers=i, json={"space": "docs", "kind": "page", "title": title}
    )
    await publish(client, team, r.json()["id"])
    return str(r.json()["id"])


async def test_acceptance_the_expiry_rule_tells_a_channel(
    client: AsyncClient, db: AsyncSession, team: Team, slack: list[dict[str, Any]], clock: Clock
) -> None:
    admin = await _admin(db, team)
    quiet = Route("C_DOCS", ["page.outdated"], {"space": "nowhere"})  # notices off
    chat = await integrations.create(
        db,
        admin,
        IntegrationData(
            IntegrationKind.slack, "Acme", {"bot_token": "xoxb-1", "signing_secret": "s"}, [quiet]
        ),
    )
    rule = {"type": "event", "event": "page.outdated"}
    step = {"type": "notify_channel", "integration": str(chat.id), "route": 0}
    await automation.create(db, admin, "Vencidos al canal", rule, [step])
    page = await _page(client, team, "Deploy")
    i = team.instance.headers
    await client.patch(f"{API}/nodes/{page}/status", headers=i, json={"status": "verified"})
    await run_jobs(db)
    assert slack == []
    clock.advance(days=91)
    await quality.outdate_expired(db)
    await run_jobs(db)
    [message] = slack
    assert message["channel"] == "C_DOCS"
    assert message["text"].startswith("“Deploy” in docs is outdated")


async def test_folio_actions_with_the_authors_permissions(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    await client.post(
        "/api/v1/projects", headers=team.instance.headers, json={"key": "DOC", "name": "Docs"}
    )
    await client.post(
        "/api/v1/projects/DOC/areas", headers=team.instance.headers, json={"name": "Docs"}
    )
    steps = [
        {"type": "folio.add_label", "label": "#Revisar"},
        {"type": "folio.create_ticket", "project": "doc", "area": "Docs"},
        {"type": "folio.change_status", "status": "in_review"},
    ]
    trigger = {"type": "event", "event": "page.published"}
    await automation.create(
        db, await _admin(db, team), "Revisar", trigger, steps, {"space": "docs"}
    )
    page = uuid.UUID(await _page(client, team, "Guía"))
    await run_jobs(db)
    run = await db.scalar(select(AutomationRun))
    assert run is not None and run.log[1].startswith("folio.create_ticket: DOC-"), run.log
    labels = await db.scalars(select(FolioNodeLabel.label).where(FolioNodeLabel.node_id == page))
    assert "revisar" in list(labels)
    link = await db.scalar(select(FolioTicketLink).where(FolioTicketLink.node_id == page))
    assert link is not None
    node = await db.get(FolioNode, page)
    assert node is not None and node.status == "in_review"


async def test_a_daily_rule_archives_what_its_query_finds(
    client: AsyncClient, db: AsyncSession, team: Team
) -> None:
    trigger = {
        "type": "schedule",
        "every": "day",
        "select": "folio.pages",
        "params": {"rql": "space = docs"},
    }
    await automation.create(
        db, await _admin(db, team), "Archivar", trigger, [{"type": "folio.archive"}]
    )
    page = uuid.UUID(await _page(client, team, "Viejo"))
    await automation.schedule(db)
    await run_jobs(db)
    node = await db.get(FolioNode, page)
    assert node is not None and node.archived_at is not None
