"""Text to RQL syntax tree, with errors that say where and what was expected."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from lark import Lark, Token, Transformer, Tree, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

from radicle.query import ast
from radicle.query.errors import RQLError

MAX_LENGTH = 2000

_READABLE = {
    "WORD": "a field or value",
    "STRING": '"quoted text"',
    "RELDATE": "a relative date like -7d",
    "FUNC": "a function like currentUser()",
    "OP": "an operator (= != > >= < <= ~ !~)",
    "TAG": "#tag",
    "AND": "AND",
    "OR": "OR",
    "NOT": "NOT",
    "IN": "IN",
    "IS": "IS",
    "EMPTY": "EMPTY",
    "ORDER": "ORDER BY",
    "BY": "BY",
    "DIRECTION": "ASC or DESC",
    "LPAR": "(",
    "RPAR": ")",
    "COMMA": ",",
    "$END": "end of query",
}


@lru_cache(maxsize=1)
def _parser() -> Lark:
    grammar = (Path(__file__).parent / "grammar.lark").read_text()
    return Lark(grammar, parser="lalr", propagate_positions=True, maybe_placeholders=False)


def _flatten[T: (ast.And, ast.Or)](cls: type[T], items: list[ast.Node]) -> T:
    flat: list[ast.Node] = []
    for item in items:
        flat.extend(item.items if isinstance(item, cls) else (item,))
    return cls(tuple(flat))


@v_args(inline=True)
class _ToAst(Transformer[Token, Any]):
    def start(self, *parts: Any) -> ast.Query:
        where = next((p for p in parts if not isinstance(p, tuple)), None)
        order = next((p for p in parts if isinstance(p, tuple)), ())
        return ast.Query(where=where, order=order)

    def or_expr(self, *items: Any) -> ast.Or:
        return _flatten(ast.Or, [i for i in items if not isinstance(i, Token)])

    def and_expr(self, *items: Any) -> ast.And:
        return _flatten(ast.And, [i for i in items if not isinstance(i, Token)])

    def not_(self, _kw: Token, item: ast.Node) -> ast.Not:
        return ast.Not(item)

    def tag_short(self, tag: Token) -> ast.Compare:
        pos = tag.start_pos or 0
        return ast.Compare("tag", pos, "=", pos, ast.Value(str(tag)[1:], "word", pos + 1))

    def value(self, token: Token) -> ast.Value:
        kinds = {"STRING": "string", "WORD": "word", "RELDATE": "reldate", "FUNC": "func"}
        return ast.Value(str(token), kinds[token.type], token.start_pos or 0)  # type: ignore[arg-type]

    def values(self, *items: ast.Value) -> tuple[ast.Value, ...]:
        return items

    def compare(self, field: Token, op: Token, value: ast.Value) -> ast.Compare:
        return ast.Compare(str(field), field.start_pos or 0, str(op), op.start_pos or 0, value)

    def in_(self, field: Token, _in: Token, values: tuple[ast.Value, ...]) -> ast.InList:
        return ast.InList(str(field), field.start_pos or 0, values, negated=False)

    def not_in(
        self, field: Token, _not: Token, _in: Token, values: tuple[ast.Value, ...]
    ) -> ast.InList:
        return ast.InList(str(field), field.start_pos or 0, values, negated=True)

    def is_empty(self, field: Token, _is: Token, _empty: Token) -> ast.IsEmpty:
        return ast.IsEmpty(str(field), field.start_pos or 0, negated=False)

    def is_not_empty(self, field: Token, _is: Token, _not: Token, _empty: Token) -> ast.IsEmpty:
        return ast.IsEmpty(str(field), field.start_pos or 0, negated=True)

    def order_by(self, _order: Token, _by: Token, *sorts: ast.Sort) -> tuple[ast.Sort, ...]:
        return sorts

    def sort(self, field: Token, direction: Token | None = None) -> ast.Sort:
        descending = direction is not None and str(direction).lower() == "desc"
        return ast.Sort(str(field), field.start_pos or 0, descending)


def parse(text: str) -> ast.Query:
    if len(text) > MAX_LENGTH:
        raise RQLError(
            f"Query is too long ({len(text)} characters); the limit is {MAX_LENGTH}.",
            position=MAX_LENGTH,
        )
    if not text.strip():
        return ast.Query(where=None, order=())
    try:
        tree: Tree[Token] = _parser().parse(text)
    except UnexpectedInput as exc:
        raise _syntax_error(text, exc) from None
    result: ast.Query = _ToAst().transform(tree)
    return result


def _syntax_error(text: str, exc: UnexpectedInput) -> RQLError:
    expected_names: set[str] = set()
    if isinstance(exc, UnexpectedToken):
        expected_names = set(exc.accepts or exc.expected)
        position = exc.token.start_pos if exc.token.type != "$END" else len(text)
        found = "end of query" if exc.token.type == "$END" else f"'{exc.token}'"
    elif isinstance(exc, UnexpectedCharacters):
        expected_names = set(exc.allowed or ())
        position = exc.pos_in_stream or 0
        found = f"'{text[position]}'"
    elif isinstance(exc, UnexpectedEOF):  # pragma: no cover - LALR reports $END tokens instead
        expected_names = set(exc.expected)
        position, found = len(text), "end of query"
    else:  # pragma: no cover
        position, found = 0, "input"
    position = position if position is not None else len(text)
    expected = sorted({_READABLE.get(name, name) for name in expected_names})
    message = f"Unexpected {found} at {position}."
    if expected:
        message += f" Expected {', '.join(expected)}."
    if found == "end of query" and "(" in text[:position] and ")" in expected:
        message += " A parenthesis is not closed."
    return RQLError(message, position=position, expected=expected)
