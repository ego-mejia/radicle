from decimal import Decimal

import pytest

from radicle.db.models import TicketType
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.services import ticket_fields as f


def test_parse_key() -> None:
    assert f.parse_key("pa-12") == ("PA", 12)
    assert f.parse_key(" WEB2-1 ") == ("WEB2", 1)
    for bad in ("PA", "PA-", "12", "P-1", "PA-x", "PA-1-2"):
        with pytest.raises(NotFound):
            f.parse_key(bad)


def test_title() -> None:
    assert f.normalize_title("  API de pagos ") == "API de pagos"
    for bad in ("", "   ", "a\nb", "x" * 256):
        with pytest.raises(ValidationFailed):
            f.normalize_title(bad)
    assert f.normalize_title("x" * 255) == "x" * 255


def test_tags() -> None:
    assert f.normalize_tags(["#Backlog", "pagos", "backlog", " ux_v2 "]) == [
        "backlog",
        "pagos",
        "ux_v2",
    ]
    for bad in (["-x"], ["has space"], ["x" * 51], ["ñ"]):
        with pytest.raises(ValidationFailed):
            f.normalize_tags(bad)
    with pytest.raises(ValidationFailed, match="at most 20"):
        f.normalize_tags([f"t{i}" for i in range(21)])
    assert len(f.normalize_tags([f"t{i}" for i in range(20)])) == 20


def test_estimate() -> None:
    assert f.normalize_estimate(8) == Decimal("8.00")
    assert f.normalize_estimate("1.005") == Decimal("1.00")
    assert f.normalize_estimate(None) is None
    assert f.normalize_estimate(9999) == Decimal("9999.00")
    for bad in (-1, 10000, "abc"):
        with pytest.raises(ValidationFailed):
            f.normalize_estimate(bad)


def test_area_required_except_drafts() -> None:
    f.require_area(TicketType.draft, None)
    for ticket_type in (TicketType.task, TicketType.bug):
        with pytest.raises(ValidationFailed, match="Area is required"):
            f.require_area(ticket_type, None)
