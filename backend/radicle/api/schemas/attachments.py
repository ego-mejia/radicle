from pydantic import Field

from radicle.api.schemas.common import Input
from radicle.api.schemas.tickets import AttachmentOut

__all__ = ["AttachmentOut", "ResizeIn"]


class ResizeIn(Input):
    preset: str = Field(description="large (2048 px), medium (1280 px) or small (800 px)")
