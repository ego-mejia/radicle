"""Folio's plugin hook (ADR 0043): `folio.register_blocks` brings editor blocks drawn in
the same sandbox as the Visual block. Their HTML passes the Visual's checks (no network,
no reaching the page, Radicle tokens) and gets its fields as `window.radicle.data`.

Radicle ships one example, `radicle.countdown`, that an admin installs in one click."""

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.services import visuals
from radicle.platform.services import plugins

HOOK = "folio.register_blocks"
BLOCKS_MAX = 20
FIELDS_MAX = 20
OPTIONS_MAX = 30
KINDS = ("text", "textarea", "number", "date", "select")
TYPE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def _where(i: int, name: str = "") -> str:
    return f"hooks.{HOOK}[{i}]" + (f".{name}" if name else "")


def _text(raw: dict[str, Any], key: str, limit: int, where: str, *, required: bool) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        need = "is required and " if required else ""
        raise plugins.invalid(where, f"{where} {need}is text of at most {limit} characters.")
    return value.strip()


def _field(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise plugins.invalid(where, f"{where} is {{key, label, kind}}.")
    key = _text(raw, "key", 40, f"{where}.key", required=True)
    if not FIELD_KEY.match(key):
        raise plugins.invalid(f"{where}.key", f"{where}.key is lowercase, like due_date.")
    kind = raw.get("kind", "text")
    if kind not in KINDS:
        raise plugins.invalid(f"{where}.kind", f"{where}.kind is one of {', '.join(KINDS)}.")
    out: dict[str, Any] = {
        "key": key,
        "label": _text(raw, "label", 80, f"{where}.label", required=True),
        "kind": kind,
        "required": bool(raw.get("required", False)),
        "default": _text(raw, "default", 2000, f"{where}.default", required=False),
    }
    if kind == "select":
        options = raw.get("options")
        if (
            not isinstance(options, list)
            or not 1 <= len(options) <= OPTIONS_MAX
            or not all(isinstance(o, str) and 0 < len(o) <= 80 for o in options)
        ):
            raise plugins.invalid(
                f"{where}.options", f"A select takes 1 to {OPTIONS_MAX} options, as text."
            )
        out["options"] = options
    return out


def _block(raw: Any, i: int) -> dict[str, Any]:
    where = _where(i)
    if not isinstance(raw, dict):
        raise plugins.invalid(where, f"{where} is {{type, name, fields, html}}.")
    kind = _text(raw, "type", 40, _where(i, "type"), required=True)
    if not TYPE.match(kind):
        raise plugins.invalid(
            _where(i, "type"), f"{_where(i, 'type')} is lowercase, like countdown."
        )
    fields = raw.get("fields", [])
    if not isinstance(fields, list) or len(fields) > FIELDS_MAX:
        raise plugins.invalid(_where(i, "fields"), f"A block has at most {FIELDS_MAX} fields.")
    checked = [_field(f, f"{_where(i, 'fields')}[{n}]") for n, f in enumerate(fields)]
    if len({f["key"] for f in checked}) != len(checked):
        raise plugins.invalid(_where(i, "fields"), "Each field of a block needs its own key.")
    html = raw.get("html")
    if not isinstance(html, str):
        raise plugins.invalid(_where(i, "html"), f"{_where(i, 'html')} is the block's HTML.")
    name = _text(raw, "name", 80, _where(i, "name"), required=True)
    report = visuals.check("html", html, description=name, title=name)
    if not report.valid:
        raise plugins.invalid(_where(i, "html"), f"{_where(i, 'html')}: {report.problems[0]}")
    return {
        "type": kind,
        "name": name,
        "description": _text(raw, "description", 300, _where(i, "description"), required=False),
        "icon": _text(raw, "icon", 8, _where(i, "icon"), required=False),
        "fields": checked,
        "html": html,
    }


def validate(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= BLOCKS_MAX:
        raise plugins.invalid(f"hooks.{HOOK}", f"{HOOK} is a list of 1 to {BLOCKS_MAX} blocks.")
    blocks = [_block(b, i) for i, b in enumerate(value)]
    if len({b["type"] for b in blocks}) != len(blocks):
        raise plugins.invalid(f"hooks.{HOOK}", "Each block of a plugin needs its own type.")
    return blocks


def example() -> dict[str, Any]:
    text = resources.files("radicle.folio.plugins").joinpath("countdown.json").read_text()
    manifest: dict[str, Any] = json.loads(text)
    return manifest


def register() -> None:
    plugins.hook(HOOK, validate)
    plugins.example(example())


@dataclass(frozen=True)
class PluginBlock:
    plugin: str
    type: str
    name: str
    description: str
    icon: str
    fields: list[dict[str, Any]]
    html: str


async def enabled_blocks(db: AsyncSession) -> list[PluginBlock]:
    """The blocks enabled plugins bring, for the editor's / menu and the reader."""
    out = []
    for c in await plugins.contributions(db, HOOK):
        for b in c.value:
            out.append(
                PluginBlock(
                    c.plugin,
                    b["type"],
                    b["name"],
                    b["description"],
                    b["icon"],
                    b["fields"],
                    b["html"],
                )
            )
    return out
