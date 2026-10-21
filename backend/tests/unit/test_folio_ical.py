"""iCal text (RFC 5545): escaping and folding long lines without splitting characters."""

from radicle.folio.services.ical import escape, fold


def test_escape() -> None:
    assert escape("a\\b; c, d\r\ne\nf") == "a\\\\b\; c\\, d\\ne\\nf"


def test_fold_keeps_lines_under_75_octets() -> None:
    line = "SUMMARY:" + "ñ" * 100
    folded = fold(line)
    parts = folded.split("\r\n ")
    assert len(parts) > 1 and all(len(p.encode()) <= 75 for p in parts)
    assert all(len(p.encode()) <= 74 for p in parts[1:])
    assert "".join(parts) == line
    assert fold("SHORT") == "SHORT"
