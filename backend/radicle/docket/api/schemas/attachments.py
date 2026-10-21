from pydantic import Field

from radicle.docket.api.schemas.tickets import AttachmentOut
from radicle.platform.api.schemas import Input

__all__ = ["AttachmentOut", "ResizeIn"]


class ResizeIn(Input):
    preset: str = Field(description="large (2048 px), medium (1280 px) or small (800 px)")
