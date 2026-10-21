"""RQL syntax tree. Every node keeps the character position it came from for errors."""

from dataclasses import dataclass
from typing import Literal

ValueKind = Literal["word", "string", "reldate", "func"]


@dataclass(frozen=True)
class Value:
    raw: str
    kind: ValueKind
    pos: int

    @property
    def text(self) -> str:
        if self.kind == "string":
            return self.raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        return self.raw


@dataclass(frozen=True)
class Compare:
    field: str
    field_pos: int
    op: str
    op_pos: int
    value: Value


@dataclass(frozen=True)
class InList:
    field: str
    field_pos: int
    values: tuple[Value, ...]
    negated: bool


@dataclass(frozen=True)
class IsEmpty:
    field: str
    field_pos: int
    negated: bool


@dataclass(frozen=True)
class And:
    items: tuple["Node", ...]


@dataclass(frozen=True)
class Or:
    items: tuple["Node", ...]


@dataclass(frozen=True)
class Not:
    item: "Node"


Node = Compare | InList | IsEmpty | And | Or | Not


@dataclass(frozen=True)
class Sort:
    field: str
    pos: int
    descending: bool


@dataclass(frozen=True)
class Query:
    where: Node | None
    order: tuple[Sort, ...]
