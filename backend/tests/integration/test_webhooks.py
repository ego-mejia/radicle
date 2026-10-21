"""Webhooks (Folio 5.5, ADR 0042): public events reach a receiver signed, once, with
retries and a log; receivers inside the network are refused."""

import json

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import DeliveryStatus, OutboxEvent, User, WebhookDelivery
from radicle.platform.errors import ValidationFailed
from radicle.platform.services import events, safe_fetch, webhooks
from tests.conftest import Team, run_jobs

events.public_event("test.happened", "Something happened (tests)")


@events.publisher("test", "happened")
async def _publish(db: AsyncSession, event: OutboxEvent) -> list[events.PublicEvent]:
    return [
        events.PublicEvent(
            "test.happened", {"what": event.payload["what"]}, {"space": event.payload["space"]}
        )
    ]


class Receiver:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.answers: list[int] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.answers.pop(0) if self.answers else 200, text="ok")


@pytest.fixture
def receiver(monkeypatch: pytest.MonkeyPatch) -> Receiver:
    got = Receiver()

    async def resolve(host: str) -> list[str]:
        return {"hooks.example.com": ["93.184.216.34"], "inside.example.com": ["10.0.0.7"]}[host]

    monkeypatch.setattr(safe_fetch, "resolve", resolve)
    monkeypatch.setattr(safe_fetch, "transport", httpx.MockTransport(got))
    return got


async def _admin(db: AsyncSession, team: Team) -> User:
    user = await db.scalar(select(User).where(User.handle == team.instance.handle))
    assert user is not None
    return user


def _data(**changes: object) -> webhooks.WebhookData:
    base: dict[str, object] = {
        "name": "CI",
        "url": "https://hooks.example.com/radicle",
        "events": ["test.happened"],
        "filter": {},
    }
    return webhooks.WebhookData(**(base | changes))  # type: ignore[arg-type]


async def test_an_event_arrives_signed_once(
    db: AsyncSession, team: Team, receiver: Receiver
) -> None:
    hook, secret = await webhooks.create(db, await _admin(db, team), _data())
    assert secret.startswith("whsec_") and secret not in hook.secret_encrypted
    await events.emit(db, "test", "happened", actor=None, payload={"what": "x", "space": "eng"})
    await run_jobs(db)
    [request] = receiver.requests
    assert request.headers["host"] == "hooks.example.com"
    assert request.headers["radicle-event"] == "test.happened"
    assert webhooks.verify(secret, request.headers["radicle-signature"], request.content)
    assert not webhooks.verify("whsec_other", request.headers["radicle-signature"], request.content)
    doc = json.loads(request.content)
    assert doc["event"] == "test.happened" and doc["data"] == {"what": "x"}
    [delivery] = await webhooks.deliveries(db, hook)
    assert delivery.status == DeliveryStatus.sent and delivery.response_status == 200
    event = await db.scalar(select(OutboxEvent))
    assert event is not None
    event.dispatched_at = None  # a crashed worker dispatches it again
    await run_jobs(db)
    assert len(receiver.requests) == 1


async def test_failures_retry_then_stay_failed(
    db: AsyncSession, team: Team, receiver: Receiver
) -> None:
    hook, _ = await webhooks.create(db, await _admin(db, team), _data())
    receiver.answers = [500, 503]
    await events.emit(db, "test", "happened", actor=None, payload={"what": "x", "space": "eng"})
    await run_jobs(db)  # the test runner ignores the backoff delay
    [delivery] = await webhooks.deliveries(db, hook)
    assert delivery.status == DeliveryStatus.sent and delivery.attempts == 3
    receiver.answers = [500] * webhooks.MAX_ATTEMPTS
    await events.emit(db, "test", "happened", actor=None, payload={"what": "y", "space": "eng"})
    await run_jobs(db)
    failed = (await webhooks.deliveries(db, hook))[0]
    assert failed.status == DeliveryStatus.failed and failed.attempts == webhooks.MAX_ATTEMPTS
    assert "HTTP 500" in (failed.last_error or "")


async def test_filters_choose_which_events(
    db: AsyncSession, team: Team, receiver: Receiver
) -> None:
    admin = await _admin(db, team)
    await webhooks.create(db, admin, _data(filter={"space": "eng"}))
    off, _ = await webhooks.create(db, admin, _data(name="Off"))
    off.active = False
    await events.emit(db, "test", "happened", actor=None, payload={"what": "a", "space": "ops"})
    await events.emit(db, "test", "happened", actor=None, payload={"what": "b", "space": "eng"})
    await run_jobs(db)
    assert [json.loads(r.content)["data"]["what"] for r in receiver.requests] == ["b"]
    assert (
        await db.scalar(select(WebhookDelivery).where(WebhookDelivery.webhook_id == off.id)) is None
    )


async def test_receivers_inside_the_network_and_bad_settings_are_refused(
    db: AsyncSession, team: Team, receiver: Receiver
) -> None:
    admin = await _admin(db, team)
    for changes, says in [
        ({"url": "http://127.0.0.1:8000/hook"}, "not a public address"),
        ({"url": "https://inside.example.com/hook"}, "not a public address"),
        ({"url": "file:///etc/passwd"}, "Only http and https"),
        ({"events": ["page.nope"]}, "Unknown events: page.nope"),
        ({"name": " "}, "Give the webhook a name"),
    ]:
        with pytest.raises(ValidationFailed, match=says):
            await webhooks.create(db, admin, _data(**changes))
    # A receiver whose DNS turns private after it was saved fails at delivery time.
    hook, _ = await webhooks.create(db, admin, _data())
    hook.url = "https://inside.example.com/hook"
    await events.emit(db, "test", "happened", actor=None, payload={"what": "z", "space": "eng"})
    await run_jobs(db)
    assert receiver.requests == []
    assert "not a public address" in ((await webhooks.deliveries(db, hook))[0].last_error or "")


def test_signatures_expire() -> None:
    header = webhooks.sign("whsec_x", 1_000, b"{}")
    assert not webhooks.verify("whsec_x", header, b"{}")
    assert not webhooks.verify("whsec_x", "garbage", b"{}")
