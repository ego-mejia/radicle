"""Where Slack and Teams call Radicle (Folio 5.4, ADR 0042). No session or token: each
request is checked against the integration's signing secret."""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import Field

from radicle.platform.api.deps import Db, HumanUser
from radicle.platform.api.schemas import Input, Output
from radicle.platform.db.models import IntegrationKind
from radicle.platform.errors import NotFound
from radicle.platform.services import chat_commands, chat_previews, integrations

router = APIRouter(tags=["integrations"])


@router.post("/hooks/chat/{integration_id}/command")
async def chat_command(integration_id: uuid.UUID, request: Request, db: Db) -> dict[str, Any]:
    """Slack slash commands (`/radicle search …`, `/radicle ask …`) and Teams outgoing
    webhooks. The answer uses the permissions of the Radicle user behind the sender."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    return await chat_commands.handle(db, integration_id, headers, await request.body())


@router.post("/hooks/chat/{integration_id}/events")
async def chat_events(integration_id: uuid.UUID, request: Request, db: Db) -> dict[str, Any]:
    """Slack's Events API (Request URL): Radicle previews its own links (`link_shared`)."""
    integration = await chat_commands.active(db, integration_id)
    if integration.kind != IntegrationKind.slack:
        raise NotFound("Events come only from Slack. Teams uses the command URL.")
    headers = {k.lower(): v for k, v in request.headers.items()}
    body = await request.body()
    secret = integrations.credentials(integration)["signing_secret"]
    chat_commands.check_slack(secret, headers, body)
    return await chat_previews.slack_event(db, integration, json.loads(body))


class ChatLinkIn(Input):
    token: str = Field(min_length=1, max_length=2000)


class ChatLinkOut(Output):
    integration: str


@router.post("/integrations/link", response_model=ChatLinkOut)
async def link_chat_account(body: ChatLinkIn, user: HumanUser, db: Db) -> ChatLinkOut:
    """Confirm that you are the Slack or Teams user who got this link from /radicle."""
    integration = await chat_commands.link(db, user, body.token)
    return ChatLinkOut(integration=integration.name)
