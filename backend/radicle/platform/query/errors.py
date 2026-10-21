import difflib

from radicle.platform.errors import ValidationFailed


class RQLError(ValidationFailed):
    """Syntax or semantic error in a query, with the character position it refers to."""

    code = "rql_error"

    def __init__(self, message: str, *, position: int, expected: list[str] | None = None) -> None:
        super().__init__(
            message,
            errors=[{"field": "q", "message": message, "position": position}],
            extra={"position": position, "expected": expected or []},
        )
        self.position = position
        self.expected = expected or []


def suggest(word: str, options: list[str] | tuple[str, ...]) -> str:
    """A hint with the closest option, or an empty string."""
    match = difflib.get_close_matches(word.lower(), list(options), n=1, cutoff=0.6)
    return f" Did you mean '{match[0]}'?" if match else ""
