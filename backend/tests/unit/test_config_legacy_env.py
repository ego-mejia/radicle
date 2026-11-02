"""ADR 0046: the RADICLE_* variables still configure the app when the new name is missing."""

import logging

import pytest

from gumball_factory.platform.config import Settings, get_settings, legacy_env_vars


def test_legacy_variable_is_read_when_the_new_one_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GUMBALL_FACTORY_TIMEZONE", raising=False)
    monkeypatch.setenv("RADICLE_TIMEZONE", "America/Mexico_City")
    assert Settings().timezone == "America/Mexico_City"


def test_new_variable_wins_over_the_legacy_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RADICLE_TIMEZONE", "America/Mexico_City")
    monkeypatch.setenv("GUMBALL_FACTORY_TIMEZONE", "Europe/Madrid")
    assert Settings().timezone == "Europe/Madrid"
    assert "RADICLE_TIMEZONE" not in legacy_env_vars()


def test_legacy_variables_are_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("GUMBALL_FACTORY_WORKDAYS", raising=False)
    monkeypatch.setenv("RADICLE_WORKDAYS", "mon,tue")
    get_settings.cache_clear()
    try:
        with caplog.at_level(logging.WARNING):
            assert get_settings().workdays == "mon,tue"
    finally:
        get_settings.cache_clear()
    assert "RADICLE_WORKDAYS" in caplog.text
