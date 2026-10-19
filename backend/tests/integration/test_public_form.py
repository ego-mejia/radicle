import io
import re
import time

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.db.models import InboxSettings, InboxSubmission, Ticket
from radicle.services import altcha, public_form
from tests.conftest import Team

API = "/api/v1"


def png(size: int = 1600) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (size, size // 2), (120, 200, 40)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
async def form(client: AsyncClient, board: Team) -> Team:
    r = await client.put(
        f"{API}/projects/PA/inbox-settings",
        headers=board.admin.headers,
        json={
            "enabled": True,
            "public_slug": "proyecto-a",
            "title": "Ayúdanos a mejorar",
            "auto_tags": ["publico"],
            "thank_you_md": "Lo leemos todo.",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["public_url"].endswith("/b/proyecto-a")
    return board


async def send(
    client: AsyncClient,
    *,
    files: list | None = None,
    age: float = 10,  # type: ignore[type-arg]
    captcha: str | None = "solve",
    **fields: str,
):
    token = public_form.form_token("proyecto-a", now=time.time() - age)
    if captcha == "solve":
        challenge = (await client.get("/b/proyecto-a/challenge")).json()
        captcha = altcha.solve(challenge)
    data = {
        "classification": "complaint",
        "title": "El pago se congela",
        "description": "Pasa al pagar con tarjeta.",
        "token": token,
        "altcha": captcha or "",
        **fields,
    }
    return await client.post(
        "/b/proyecto-a", data=data, files=[("files", f) for f in files or []] or None
    )


def code_of(html: str) -> str:
    match = re.search(r'data-testid="tracking-code">([0-9A-Z]{10})<', html)
    assert match, html[:400]
    return match.group(1)


async def test_disabled_form_is_404(client: AsyncClient, board: Team) -> None:
    assert (await client.get("/b/pa")).status_code == 404
    r = await client.put(
        f"{API}/projects/PA/inbox-settings", headers=board.member.headers, json={"enabled": True}
    )
    assert r.status_code == 403
    r = await client.get(f"{API}/projects/PA/inbox-settings", headers=board.admin.headers)
    assert (r.json()["enabled"], r.json()["public_slug"]) == (False, "pa")


async def test_acceptance_send_a_complaint_and_track_it(
    client: AsyncClient, db: AsyncSession, form: Team
) -> None:
    page = await client.get("/b/proyecto-a", headers={"accept-language": "es-MX,es;q=0.9"})
    assert page.status_code == 200 and "Ayúdanos a mejorar" in page.text
    assert "Queja" in page.text and 'name="website"' in page.text
    r = await send(
        client, files=[("captura.png", png(), "image/png")], name="Ana", email="ana@example.com"
    )
    assert r.status_code == 201, r.text[:500]
    code = code_of(r.text)
    assert "Lo leemos todo." in r.text

    ticket = await db.scalar(select(Ticket).where(Ticket.tracking_code == code))
    assert ticket is not None
    assert (ticket.type.value, ticket.origin.value, ticket.classification.value) == (
        "draft",
        "user",
        "complaint",
    )
    assert ticket.tags == ["publico"] and ticket.submitter_email == "ana@example.com"
    t = (await client.get(f"{API}/tickets/PA-1", headers=form.member.headers)).json()
    assert t["reporter"]["handle"] == "inbox" and t["origin"] == "user"
    assert t["attachments"][0]["width"] == 1280  # shrunk to medium
    inbox = (await client.get(f"{API}/projects/PA/inbox", headers=form.viewer.headers)).json()
    assert [i["key"] for i in inbox["items"]] == ["PA-1"]

    tracking = await client.get(f"/b/proyecto-a/t/{code}")
    assert tracking.status_code == 200 and "Received" in tracking.text
    assert "PA-1" not in tracking.text and "inbox" not in tracking.text
    r = await client.post(
        f"{API}/tickets/PA-1/inbox/approve",
        headers=form.member.headers,
        json={"type": "bug", "area": "Backend", "assignee": "luis"},
    )
    assert r.status_code == 200, r.text
    tracking = await client.get(f"/b/proyecto-a/t/{code.lower()}")
    assert "Accepted" in tracking.text
    for secret in ("PA-1", "luis", "Backend", "bug"):
        assert secret not in tracking.text
    assert (await client.get("/b/proyecto-a/t/0000000000")).status_code == 404


async def test_discarded_shows_the_public_note(client: AsyncClient, form: Team) -> None:
    code = code_of((await send(client)).text)
    await client.post(
        f"{API}/tickets/PA-1/comments",
        headers=form.member.headers,
        json={"body_md": "Comentario interno"},
    )
    await client.post(
        f"{API}/tickets/PA-1/inbox/discard",
        headers=form.member.headers,
        json={"public_comment": "Ya está en el plan de V2."},
    )
    page = (await client.get(f"/b/proyecto-a/t/{code}")).text
    assert "Closed" in page and "Ya está en el plan de V2." in page
    assert "Comentario interno" not in page


async def test_spam_checks_all_look_the_same(
    client: AsyncClient, db: AsyncSession, form: Team
) -> None:
    generic = "We could not send it"
    cases = [
        await send(client, website="http://spam.example"),  # honeypot
        await send(client, age=1),  # too fast
        await send(client, captcha="bm90IGpzb24="),  # broken ALTCHA
        await send(client, description=" ".join(f"https://x{i}.example" for i in range(6))),
    ]
    for r in cases:
        assert r.status_code == 422 and generic in r.text, r.text[:300]
    # A solved challenge cannot be used twice.
    challenge = altcha.solve((await client.get("/b/proyecto-a/challenge")).json())
    assert (await send(client, captcha=challenge)).status_code == 201
    r = await send(client, captcha=challenge)
    assert r.status_code == 422 and generic in r.text
    assert await db.scalar(select(Ticket.id).where(Ticket.number == 2)) is None


async def test_sixth_submission_in_an_hour_is_blocked(
    client: AsyncClient, db: AsyncSession, form: Team
) -> None:
    project_id = await db.scalar(select(InboxSettings.project_id))
    for _ in range(5):
        db.add(InboxSubmission(project_id=project_id, ip_hash=public_form.ip_hash("10.0.0.1")))
    await db.commit()
    r = await send(client)
    assert r.status_code == 422 and "We could not send it" in r.text


async def test_fields_files_and_escaping(client: AsyncClient, db: AsyncSession, form: Team) -> None:
    r = await send(client, title="abc")
    assert r.status_code == 422 and "Check the length" in r.text
    r = await send(client, classification="experiment")
    assert r.status_code == 422 and "Choose one" in r.text
    r = await send(client, files=[("notas.txt", b"hola", "text/plain")])
    assert r.status_code == 422 and "Only images and PDF" in r.text
    r = await send(client, files=[("a.png", png(200), "image/png")] * 4)
    assert r.status_code == 422 and "Too many files" in r.text
    await client.put(
        f"{API}/projects/PA/inbox-settings",
        headers=form.admin.headers,
        json={"require_email": True},
    )
    r = await send(client)
    assert r.status_code == 422 and "Required" in r.text

    r = await send(
        client,
        email="x@example.com",
        title="<b>Hola</b> mundo",
        description="<script>alert(1)</script> **negrita** [x](javascript:1)",
    )
    assert r.status_code == 201
    ticket = await db.scalar(select(Ticket).where(Ticket.number == 1))
    assert ticket is not None
    assert (
        "\\<script\\>" in ticket.description_md and "\\*\\*negrita\\*\\*" in ticket.description_md
    )
    page = (await client.get(f"/b/proyecto-a/t/{ticket.tracking_code}")).text
    assert "<b>Hola</b>" not in page and "&lt;b&gt;Hola&lt;/b&gt;" in page


async def test_captcha_secrets_are_encrypted(
    client: AsyncClient, db: AsyncSession, form: Team
) -> None:
    r = await client.put(
        f"{API}/projects/PA/inbox-settings",
        headers=form.admin.headers,
        json={"captcha": "turnstile"},
    )
    assert r.status_code == 422 and "site key and secret" in r.json()["detail"]
    r = await client.put(
        f"{API}/projects/PA/inbox-settings",
        headers=form.admin.headers,
        json={"captcha": "turnstile", "captcha_site_key": "site", "captcha_secret": "top-secret"},
    )
    assert r.status_code == 200 and r.json()["captcha_has_secret"] is True
    assert "top-secret" not in r.text
    row = await db.scalar(select(InboxSettings))
    assert row is not None and row.captcha_config["secret"].startswith("v1:")
    assert "top-secret" not in row.captcha_config["secret"]
    r = await client.put(
        f"{API}/projects/PA/inbox-settings", headers=form.admin.headers, json={"public_slug": "A B"}
    )
    assert r.status_code == 422


def test_tracking_codes_are_50_bits() -> None:
    assert len(public_form.CODE_ALPHABET) == 32 and public_form.CODE_LENGTH == 10
    assert not set("ILOU") & set(public_form.CODE_ALPHABET)


async def test_tracking_is_rate_limited(client: AsyncClient, form: Team) -> None:
    codes = [(await client.get("/b/proyecto-a/t/AAAAAAAAAA")).status_code for _ in range(21)]
    assert codes[:20] == [404] * 20 and codes[20] == 429
