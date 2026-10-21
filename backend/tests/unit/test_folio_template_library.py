"""The templates Folio ships with are valid documents with the variables they promise."""

import pytest

from radicle.folio.services import schema
from radicle.folio.services.parse_markdown import from_markdown
from radicle.folio.services.template_library import BUILTINS


def test_keys_are_unique() -> None:
    keys = [b.key for b in BUILTINS]
    assert len(keys) == len(set(keys)) == 6 and "build-spec" in keys


@pytest.mark.parametrize("builtin", BUILTINS, ids=lambda b: b.key)
def test_each_template_is_a_valid_document(builtin: object) -> None:
    doc = from_markdown(builtin.markdown)  # type: ignore[attr-defined]
    assert schema.validate(doc) == doc


def test_the_build_spec_has_its_sections() -> None:
    spec = next(b for b in BUILTINS if b.key == "build-spec")
    for section in ("Objetivo y alcance", "Entregables", "Modelo de datos", "API y MCP", "Tests"):
        assert f"## {section}" in spec.markdown
    assert spec.doc_type == "build-spec"
