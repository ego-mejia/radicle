"""Slack and Teams integrations (Folio 5.4): credentials are checked and kept encrypted,
and the admin's view never shows a secret."""

import base64

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import IntegrationKind, User
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import integrations
from radicle.platform.services.integrations import IntegrationData, Route
from tests.conftest import Team

SLACK = {"bot_token": "xoxb-1-2-abc", "signing_secret": "8f742231b10e8888abcd99yyyzzz85a5"}
TEAMS = {"secret": base64.b64encode(b"teams-shared-secret").decode()}
HOOK = "https://93.184.216.34/webhookb2/abc"


async def _admin(db: AsyncSession, team: Team) -> User:
    user = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert user is not None
    return user


async def test_slack_and_teams_keep_their_secrets(db: AsyncSession, team: Team) -> None:
    admin = await _admin(db, team)
    notices = [Route("C0ANUNCIOS", ["page.published"], {"space": "anuncios"})]
    slack = await integrations.create(
        db, admin, IntegrationData(IntegrationKind.slack, "Acme", SLACK, notices)
    )
    assert "xoxb" not in slack.credentials_encrypted
    assert integrations.credentials(slack) == SLACK
    assert integrations.view(slack)["notices"][0]["channel"] == "C0ANUNCIOS"
    teams = await integrations.create(
        db, admin, IntegrationData(IntegrationKind.teams, "Acme Teams", TEAMS, [Route(HOOK)])
    )
    assert HOOK not in str(teams.config) and integrations.routes(teams)[0].channel == HOOK
    assert integrations.view(teams)["notices"][0]["channel"] == "93.184.216.34/…"
    assert "secret" not in str(integrations.view(teams))
    # Updating without credentials keeps them; routes are replaced.
    await integrations.update(
        db, slack, IntegrationData(IntegrationKind.slack, "Acme 2", None, [Route("C0OTRO")])
    )
    assert integrations.credentials(slack) == SLACK
    assert [r.channel for r in integrations.routes(slack)] == ["C0OTRO"]
    assert [i.name for i in await integrations.list_all(db)] == ["Acme 2", "Acme Teams"]


@pytest.mark.parametrize(
    ("kind", "creds", "notices", "says"),
    [
        (IntegrationKind.slack, {"bot_token": "xoxp-user"}, [], "starts with xoxb-"),
        (IntegrationKind.slack, {"bot_token": "xoxb-1"}, [], "signing secret"),
        (IntegrationKind.teams, {"secret": "not base64!"}, [], "base64"),
        (IntegrationKind.slack, SLACK, [Route(" ")], "Slack channel id"),
        (IntegrationKind.slack, SLACK, [Route("C1", ["nope"])], "Unknown events: nope"),
        (IntegrationKind.teams, TEAMS, [Route("http://10.0.0.1/hook")], "not a public address"),
        (IntegrationKind.slack, None, [], "Send the credentials"),
    ],
)
async def test_bad_settings_say_how_to_fix(
    db: AsyncSession,
    team: Team,
    kind: IntegrationKind,
    creds: dict[str, str] | None,
    notices: list[Route],
    says: str,
) -> None:
    with pytest.raises(ValidationFailed, match=says):
        await integrations.create(
            db, await _admin(db, team), IntegrationData(kind, "X", creds, notices)
        )
