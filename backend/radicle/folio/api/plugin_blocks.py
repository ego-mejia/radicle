"""The editor blocks that enabled plugins bring (Folio 5.7, ADR 0043), for the / menu and
for reading pages that use them."""

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field

from radicle.folio.services import plugin_blocks
from radicle.platform import authz
from radicle.platform.api.deps import CurrentPrincipal, Db
from radicle.platform.api.schemas import Output

router = APIRouter(tags=["folio"])


class PluginBlockField(Output):
    key: str
    label: str
    kind: Literal["text", "textarea", "number", "date", "select"]
    required: bool
    default: str
    options: list[str] = Field(default_factory=list)


class PluginBlockOut(Output):
    id: str = Field(description="plugin/type, as pages name the block")
    plugin: str
    type: str
    name: str
    description: str
    icon: str
    fields: list[PluginBlockField]
    html: str = Field(description="Drawn in the Visual block's sandbox, with the data")


class PluginBlocksOut(Output):
    items: list[PluginBlockOut]


def _field(f: dict[str, Any]) -> PluginBlockField:
    return PluginBlockField.model_validate(f)


@router.get("/plugin-blocks", response_model=PluginBlocksOut)
async def list_plugin_blocks(principal: CurrentPrincipal, db: Db) -> PluginBlocksOut:
    """Blocks of the plugins that are on; a turned-off plugin's blocks are not here."""
    (await authz.authorize(db, principal.user, "folio", "folio.read")).raise_if_denied()
    blocks = await plugin_blocks.enabled_blocks(db)
    return PluginBlocksOut(
        items=[
            PluginBlockOut(
                id=f"{b.plugin}/{b.type}",
                plugin=b.plugin,
                type=b.type,
                name=b.name,
                description=b.description,
                icon=b.icon,
                fields=[_field(f) for f in b.fields],
                html=b.html,
            )
            for b in blocks
        ]
    )
