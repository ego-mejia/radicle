import pytest

from radicle.platform.errors import ValidationFailed
from radicle.platform.services import validation


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("luis", "luis"),
        ("@Luis", "luis"),
        ("agent-backend", "agent-backend"),
        ("a_1", "a_1"),
        ("  ana ", "ana"),
        ("x" * 32, "x" * 32),
    ],
)
def test_valid_handles(raw: str, expected: str) -> None:
    assert validation.normalize_handle(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "a", "-ana", "_ana", "ana luis", "ana.luis", "x" * 33, "ñandu"]
)
def test_invalid_handles(raw: str) -> None:
    with pytest.raises(ValidationFailed, match="Invalid handle"):
        validation.normalize_handle(raw)


def test_display_name_collapses_whitespace() -> None:
    assert validation.normalize_display_name("  Ana   María ") == "Ana María"


@pytest.mark.parametrize("raw", ["", "   ", "x" * 101])
def test_invalid_display_names(raw: str) -> None:
    with pytest.raises(ValidationFailed):
        validation.normalize_display_name(raw)


@pytest.mark.parametrize("raw", ["short", "x" * 257])
def test_invalid_passwords(raw: str) -> None:
    with pytest.raises(ValidationFailed, match="Password must be"):
        validation.check_password(raw)


def test_password_bounds() -> None:
    assert validation.check_password("x" * 8) == "x" * 8
    assert validation.check_password("x" * 256) == "x" * 256


@pytest.mark.parametrize("raw", ["", "  ", "x" * 101])
def test_invalid_token_names(raw: str) -> None:
    with pytest.raises(ValidationFailed):
        validation.normalize_token_name(raw)
