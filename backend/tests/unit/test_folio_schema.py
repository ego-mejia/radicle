"""Folio's document schema (Folio 1.2): every phase 1 block passes; anything else is a 422
with the path of the problem."""

import copy
from typing import Any

import pytest

from radicle.folio.services import schema
from radicle.folio.services.schema import SchemaError
from tests.unit.folio_docs import EVERY_BLOCK, block, p, t


def test_every_block_of_phase_1_validates() -> None:
    assert schema.validate(copy.deepcopy(EVERY_BLOCK)) == EVERY_BLOCK
    assert schema.validate(schema.empty())["content"] == []


def doc(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(blocks)}


@pytest.mark.parametrize(
    ("document", "path", "message"),
    [
        ({"type": "page"}, "$", "a document is"),
        (doc({"type": "script"}), "$.content[0]", "not a block"),
        (doc(t("suelto")), "$.content[0]", "not a block"),
        (doc(block("listItem", p(t("x")))), "$.content[0]", "not a block"),
        (doc(block("heading", t("x"), level=7)), "$.content[0].attrs.level", "one of"),
        (doc(block("heading", t("x"))), "$.content[0].attrs.level", "required"),
        (doc(block("panel", p(t("x")), kind="danger")), "$.content[0].attrs.kind", "one of"),
        (
            doc(block("panel", p(t("x")), kind="info", color="red")),
            "$.content[0].attrs.color",
            "unknown",
        ),
        (doc(p(block("paragraph"))), "$.content[0].content[0]", "cannot go inside paragraph"),
        (doc(block("bulletList")), "$.content[0].content", "at least 1"),
        (
            doc(block("columns", block("column", p(t("x"))), layout="two")),
            "$.content[0].content",
            "at least 2",
        ),
        (doc(block("codeBlock", t("x", "bold"))), "$.content[0].content[0]", "plain text"),
        (doc(p({"type": "text", "text": ""})), "$.content[0].content[0]", "non-empty"),
        (doc(p(t("x", "blink"))), "$.content[0].content[0].marks[0]", "unknown mark"),
        (
            doc(p(t("x", "link", href="javascript:alert(1)"))),
            "$.content[0].content[0].marks[0].attrs.href",
            "http",
        ),
        (
            doc(block("orderedList", block("listItem", p(t("x"))), start=True)),
            "$.content[0].attrs.start",
            "number",
        ),
        (doc({"type": "paragraph", "onclick": "x"}), "$.content[0]", "unexpected keys"),
        (doc(block("file", name="x.pdf")), "$.content[0].attrs.assetId", "required"),
    ],
)
def test_rejects_with_the_path(document: dict[str, Any], path: str, message: str) -> None:
    with pytest.raises(SchemaError, match=message) as exc:
        schema.validate(document)
    assert exc.value.errors[0]["field"] == path
    assert exc.value.status == 422


def test_limits_depth_and_size() -> None:
    deep: dict[str, Any] = p(t("x"))
    for _ in range(schema.MAX_DEPTH + 1):
        deep = block("blockquote", deep)
    with pytest.raises(SchemaError, match="deeper"):
        schema.validate(doc(deep))
    huge = doc(*[p(t("x")) for _ in range(schema.MAX_NODES)])
    with pytest.raises(SchemaError, match="at most"):
        schema.validate(huge)
