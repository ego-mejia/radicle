"""Where Slack and Teams call Radicle (Folio 5.4, ADR 0042). No session or token: each
request is checked against the integration's signing secret."""

import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import Field

from radicle.platform.api.deps import Db, HumanUser
from radicle.platform.api.schemas import Input, Output
from radicle.platform.services import chat_commands

router = APIRouter(tags=["integrations"])


@router.post("/hooks/chat/{integration_id}/command")
async def chat_command(integration_id: uuid.UUID, request: Request, db: Db) -> dict[str, Any]:
    """Slack slash commands (`/radicle search …`, `/radicle ask …`) and Teams outgoing
    webhooks. The answer uses the permissions of the Radicle user behind the sender."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    return await chat_commands.handle(db, integration_id, headers, await request.body())


class ChatLinkIn(Input):
    token: str = Field(min_length=1, max_length=2000)


class ChatLinkOut(Output):
    integration: str


@router.post("/integrations/link", response_model=ChatLinkOut)
async def link_chat_account(body: ChatLinkIn, user: HumanUser, db: Db) -> ChatLinkOut:
    """Confirm that you are the Slack or Teams user who got this link from /radicle."""
    integration = await chat_commands.link(db, user, body.token)
    return ChatLinkOut(integration=integration.name)
