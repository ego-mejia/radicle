"""Admin, Plugins (Folio 5.7, shared with Docket; ADR 0043): install a plugin from its
JSON manifest, turn it on or off, remove it. Instance admins only."""

from typing import Any

from fastapi import APIRouter, Response
from pydantic import Field

from radicle.platform.api.deps import Db, InstanceAdmin
from radicle.platform.api.schemas import Input, Output, UtcDatetime
from radicle.platform.db.models import Plugin
from radicle.platform.services import plugins

router = APIRouter(tags=["plugins"])


class PluginOut(Output):
    key: str
    name: str
    version: str
    description: str
    author: str
    enabled: bool
    hooks: list[str] = Field(description="The hooks it brings, e.g. folio.register_blocks")
    manifest: dict[str, Any]
    installed_at: UtcDatetime
    updated_at: UtcDatetime


class PluginsOut(Output):
    items: list[PluginOut]
    hooks: list[str] = Field(description="Hooks this instance knows")


class PluginIn(Input):
    manifest: dict[str, Any] = Field(description="The plugin's JSON manifest (ADR 0043)")


class PluginPatch(Input):
    enabled: bool


def _out(p: Plugin) -> PluginOut:
    return PluginOut(
        key=p.key,
        name=p.name,
        version=p.version,
        description=p.description,
        author=p.author,
        enabled=p.enabled,
        hooks=sorted(p.manifest.get("hooks", {})),
        manifest=p.manifest,
        installed_at=p.installed_at,
        updated_at=p.updated_at,
    )


@router.get("/admin/plugins", response_model=PluginsOut)
async def list_plugins(admin: InstanceAdmin, db: Db) -> PluginsOut:
    """Installed plugins, and the hooks a manifest may use."""
    rows = await plugins.list_plugins(db)
    return PluginsOut(items=[_out(p) for p in rows], hooks=plugins.hook_names())


@router.post("/admin/plugins", response_model=PluginOut, status_code=201)
async def install_plugin(body: PluginIn, admin: InstanceAdmin, db: Db) -> PluginOut:
    """Install a plugin; a manifest with an installed key replaces it (an update)."""
    return _out(await plugins.install(db, admin, body.manifest))


@router.patch("/admin/plugins/{key}", response_model=PluginOut)
async def patch_plugin(key: str, body: PluginPatch, admin: InstanceAdmin, db: Db) -> PluginOut:
    """Turn a plugin on or off; off, what it brings leaves the apps but stays saved."""
    plugin = await plugins.get_plugin(db, key)
    return _out(await plugins.set_enabled(db, admin, plugin, body.enabled))


@router.delete("/admin/plugins/{key}", status_code=204)
async def delete_plugin(key: str, admin: InstanceAdmin, db: Db) -> Response:
    await plugins.remove(db, admin, await plugins.get_plugin(db, key))
    return Response(status_code=204)
