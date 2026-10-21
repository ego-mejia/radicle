"""Email notifications over SMTP (ADR 0038). Each delivery is its own job; a failed send
queues itself again with a growing delay, and after the last attempt the delivery keeps
the error."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.config import Settings, get_settings
from radicle.platform.db.models import DeliveryStatus, EventDelivery, User, utcnow
from radicle.platform.services import queue
from radicle.platform.services.events import EMAIL_JOB

MAX_ATTEMPTS = 5


def build(settings: Settings, to: str, subject: str, body: str, link: str | None) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    url = f"{settings.base_url.rstrip('/')}{link}" if link and link.startswith("/") else link
    text = "\n\n".join(part for part in (body, url or "") if part)
    message.set_content(text or subject)
    return message


def send(settings: Settings, message: EmailMessage) -> None:
    """Blocking send; called in a thread."""
    host, port = settings.smtp_host or "", settings.smtp_port
    if port == 465:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    with server:
        if port != 465 and settings.smtp_tls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password or "")
        server.send_message(message)


@queue.handler(EMAIL_JOB)
async def send_delivery(
    db: AsyncSession, delivery_id: int, subject: str, body: str, link: str | None, **_: Any
) -> None:
    delivery = await db.get(EventDelivery, delivery_id)
    if delivery is None or delivery.status != DeliveryStatus.pending:
        return
    user = await db.get(User, delivery.user_id)
    settings = get_settings()
    if user is None or not user.email or not settings.smtp_host:
        delivery.status = DeliveryStatus.skipped
        delivery.last_error = "No email address" if settings.smtp_host else "SMTP is off"
        return
    delivery.attempts += 1
    try:
        await asyncio.to_thread(send, settings, build(settings, user.email, subject, body, link))
    except (OSError, smtplib.SMTPException) as exc:
        delivery.last_error = f"{type(exc).__name__}: {exc}"[:500]
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = DeliveryStatus.failed
            return
        await queue.enqueue(
            db,
            EMAIL_JOB,
            delay_seconds=60 * delivery.attempts,
            delivery_id=delivery_id,
            subject=subject,
            body=body,
            link=link,
        )
        return
    delivery.status = DeliveryStatus.sent
    delivery.sent_at = utcnow()
