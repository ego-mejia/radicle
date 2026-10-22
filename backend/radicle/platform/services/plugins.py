"""Plugins (ADR 0043): JSON manifests an instance admin installs, enables and removes.

A manifest names hooks; each app registers the hooks it reads with a validator
(`hook("folio.register_blocks", validate)`) and asks for what enabled plugins give it with
`contributions(name)`. Platform never runs plugin code: apps draw what plugins bring in a
sandbox."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.platform.db.models import AuditApp, Plugin, User
from radicle.platform.errors import NotFound, ValidationFailed
from radicle.platform.services import audit

KEY = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
MANIFEST_MAX = 2_000_000  # bytes of JSON

# A hook's validator gets the hook's value from a manifest and returns it normalized, or
# raises ValidationFailed saying what is wrong.
Validator = Callable[[Any], Any]
_hooks: dict[str, Validator] = {}


def hook(name: str, validate: Validator) -> None:
    _hooks[name] = validate


def hook_names() -> list[str]:
    return sorted(_hooks)


def invalid(field: str, message: str) -> ValidationFailed:
    return ValidationFailed(message, errors=[{"field": field, "message": "invalid"}])


def _text(manifest: dict[str, Any], field: str, limit: int, *, required: bool = True) -> str:
    value = manifest.get(field, "")
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        need = "is required and " if required else ""
        raise invalid(field, f"{field} {need}is text of at most {limit} characters.")
    return value.strip()


def validate(manifest: Any) -> dict[str, Any]:
    """The manifest normalized, each hook checked by the app that registered it."""
    if not isinstance(manifest, dict):
        raise invalid("manifest", "A plugin is a JSON object: {key, name, version, hooks}.")
    key = _text(manifest, "key", 80)
    if not KEY.match(key):
        raise invalid(
            "key", "key is lowercase words joined by dots or dashes, e.g. acme.countdown."
        )
    version = _text(manifest, "version", 40)
    if not VERSION.match(version):
        raise invalid("version", "version is semver, e.g. 1.0.0.")
    hooks = manifest.get("hooks")
    if not isinstance(hooks, dict) or not hooks:
        known = ", ".join(hook_names()) or "none yet"
        raise invalid("hooks", f"A plugin brings at least one hook. Known hooks: {known}.")
    checked: dict[str, Any] = {}
    for name, value in hooks.items():
        validator = _hooks.get(name)
        if validator is None:
            known = ", ".join(hook_names()) or "none yet"
            raise invalid(f"hooks.{name}", f"Unknown hook {name}. Known hooks: {known}.")
        checked[name] = validator(value)
    return {
        "key": key,
        "name": _text(manifest, "name", 80),
        "version": version,
        "description": _text(manifest, "description", 500, required=False),
        "author": _text(manifest, "author", 120, required=False),
        "hooks": checked,
    }


async def list_plugins(db: AsyncSession) -> list[Plugin]:
    return list(await db.scalars(select(Plugin).order_by(Plugin.name, Plugin.key)))


async def get_plugin(db: AsyncSession, key: str) -> Plugin:
    found = await db.scalar(select(Plugin).where(Plugin.key == key))
    if found is None:
        raise NotFound(
            f"No plugin {key}. GET /api/v1/admin/plugins lists the installed ones.",
            code="plugin_not_found",
        )
    return found


async def install(db: AsyncSession, actor: User, manifest: Any) -> Plugin:
    """Install a plugin, or replace the manifest of the one with the same key."""
    clean = validate(manifest)
    found = await db.scalar(select(Plugin).where(Plugin.key == clean["key"]))
    before = {"version": found.version} if found else None
    plugin = found or Plugin(key=clean["key"], installed_by=actor.id, enabled=True)
    plugin.name, plugin.version = clean["name"], clean["version"]
    plugin.description, plugin.author = clean["description"], clean["author"]
    plugin.manifest = clean
    if found is None:
        db.add(plugin)
    await db.flush()
    audit.record(
        db,
        actor,
        "plugin.install" if found is None else "plugin.update",
        target_type="plugin",
        target_id=plugin.key,
        before=before,
        after={"version": plugin.version, "hooks": sorted(clean["hooks"])},
        app=AuditApp.platform,
    )
    return plugin


async def set_enabled(db: AsyncSession, actor: User, plugin: Plugin, enabled: bool) -> Plugin:
    if plugin.enabled != enabled:
        plugin.enabled = enabled
        await db.flush()
        audit.record(
            db,
            actor,
            "plugin.update",
            target_type="plugin",
            target_id=plugin.key,
            after={"enabled": enabled},
            app=AuditApp.platform,
        )
    return plugin


async def remove(db: AsyncSession, actor: User, plugin: Plugin) -> None:
    await db.delete(plugin)
    await db.flush()
    audit.record(
        db,
        actor,
        "plugin.delete",
        target_type="plugin",
        target_id=plugin.key,
        app=AuditApp.platform,
    )


@dataclass(frozen=True)
class Contribution:
    plugin: str
    value: Any


async def contributions(db: AsyncSession, name: str) -> list[Contribution]:
    """What each enabled plugin brings to the hook, by plugin name."""
    rows = await db.scalars(
        select(Plugin).where(Plugin.enabled.is_(True)).order_by(Plugin.name, Plugin.key)
    )
    return [
        Contribution(p.key, p.manifest["hooks"][name])
        for p in rows
        if name in p.manifest.get("hooks", {})
    ]
