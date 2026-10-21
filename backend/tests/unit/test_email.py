"""SMTP sending (ADR 0038): STARTTLS, implicit TLS on 465, and login when configured."""

from typing import Any, ClassVar

import pytest

from radicle.platform.config import Settings
from radicle.platform.services import email


class FakeSMTP:
    instances: ClassVar[list["FakeSMTP"]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host, self.port, self.calls = host, port, []  # type: ignore[var-annotated]
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: Any) -> None:
        self.calls.append("quit")

    def starttls(self, context: Any) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login {user}")

    def send_message(self, message: Any) -> None:
        self.calls.append(f"send {message['To']}")


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSMTP.instances = []
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", FakeSMTP)


def test_starttls_and_login() -> None:
    settings = Settings(smtp_host="mail.test", smtp_user="bot", smtp_password="pw")
    email.send(settings, email.build(settings, "ana@x.test", "Hola", "Cuerpo", "/folio"))
    assert FakeSMTP.instances[0].calls == ["starttls", "login bot", "send ana@x.test", "quit"]


def test_implicit_tls_without_login() -> None:
    settings = Settings(smtp_host="mail.test", smtp_port=465)
    message = email.build(settings, "ana@x.test", "Hola", "", "https://elsewhere.test/a")
    email.send(settings, message)
    assert FakeSMTP.instances[0].calls == ["send ana@x.test", "quit"]
    assert message.get_content().strip() == "https://elsewhere.test/a"
