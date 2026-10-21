from pydantic import Field

from radicle.docket.db.models import ScreenOperation, TicketType
from radicle.platform.api.schemas import Input, Output


class ScreenFieldIn(Input):
    field: str = Field(description="title, area, ... or cf.<key>")
    required: bool = False


class ScreenIn(Input):
    type: TicketType
    operation: ScreenOperation
    transition: str | None = Field(
        default=None, description="Transition ref or name; only for operation = transition"
    )
    fields: list[ScreenFieldIn]


class ScreensPut(Input):
    screens: list[ScreenIn]


class ScreenFieldOut(Output):
    field: str
    required: bool


class ScreenOut(Output):
    type: TicketType
    operation: ScreenOperation
    transition: str | None = Field(description="Transition ref")
    transition_name: str | None
    fields: list[ScreenFieldOut]


class SchemaFieldOut(Output):
    field: str
    label: str
    kind: str = Field(description="text, markdown, enum, area, milestone, user, users, ...")
    required: bool
    options: list[str] | None = None
    areas: list[str] | None = Field(
        default=None, description="Custom fields shown only for these areas"
    )


class FormSchemaOut(Output):
    type: TicketType
    operation: ScreenOperation
    transition: str | None
    from_screen: bool = Field(description="False means the stage 1 defaults apply")
    fields: list[SchemaFieldOut]
