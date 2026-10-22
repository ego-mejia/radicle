"""The signed print link the worker's browser opens for a PDF export."""

import uuid

from radicle.folio.services.exporting import print_link

ID = uuid.UUID("0b5c2a4e-1111-4111-8111-111111111111")


def test_a_token_opens_its_export_for_a_while() -> None:
    token = print_link.token(ID, now=1_000)
    assert print_link.export_of(token, now=1_000 + 60) == ID
    assert print_link.export_of(token, now=1_000 + print_link.PRINT_SECONDS + 1) is None


def test_forged_or_broken_tokens_open_nothing() -> None:
    token = print_link.token(ID, now=1_000)
    other = uuid.UUID("0b5c2a4e-2222-4222-8222-222222222222")
    forged = token.replace(str(ID), str(other))
    assert print_link.export_of(forged, now=1_000) is None
    assert print_link.export_of("nope", now=1_000) is None
    assert print_link.export_of(f"{ID}.x.y", now=1_000) is None
