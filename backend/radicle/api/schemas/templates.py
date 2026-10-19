from typing import Any

from pydantic import Field

from radicle.api.schemas.common import Input, Output, UtcDatetime
from radicle.db.models import SyncStatus
from radicle.services.template_config import TemplateConfig, WorkflowConf

MAPPINGS_HELP = (
    'Where tickets of removed statuses go, by ref: {"in_review": "in_progress"} for every '
    'type, or {"task": {"in_review": "in_progress"}} per type'
)


class LinkedProjectOut(Output):
    key: str
    name: str
    template_version: int | None
    in_sync: bool


class TemplateOut(Output):
    id: str
    name: str
    description_md: str
    version: int
    archived: bool
    is_default: bool
    linked_projects: list[LinkedProjectOut]
    created_at: UtcDatetime
    updated_at: UtcDatetime


class TemplateDetail(TemplateOut):
    config: TemplateConfig
    warnings: list[str] = Field(default_factory=list, description="e.g. unreachable statuses")


class TemplateCreate(Input):
    name: str
    description_md: str = ""
    config: TemplateConfig | None = Field(default=None, description="Default: Radicle default")


class TemplatePatch(Input):
    """Sending `config` replaces it, bumps the version and syncs every linked project."""

    name: str | None = None
    description_md: str | None = None
    config: TemplateConfig | None = None
    status_mappings: dict[str, Any] | None = Field(default=None, description=MAPPINGS_HELP)


class SyncRunOut(Output):
    id: str
    project: str
    template_version: int
    status: SyncStatus
    error: str | None
    created_at: UtcDatetime
    started_at: UtcDatetime | None
    finished_at: UtcDatetime | None


class SaveAsTemplateIn(Input):
    name: str
    description_md: str = ""


class WorkflowPut(Input):
    workflow: WorkflowConf
    status_mappings: dict[str, Any] | None = Field(default=None, description=MAPPINGS_HELP)


class WorkflowPutOut(Output):
    warnings: list[str]


def config_dict(config: TemplateConfig | None) -> dict[str, Any] | None:
    return config.model_dump(mode="json", by_alias=True) if config is not None else None
