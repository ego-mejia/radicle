"""Fractional indexing: string keys that sort lexicographically and always fit between two.

Keys use base62 digits in ASCII order. `between(a, b)` returns a key strictly between
`a` and `b`, where None means the start or end of the list. Same scheme as the
fractional-indexing library: an integer part plus a fraction that never ends in the
lowest digit, so there is always room before any key.
"""

import string

DIGITS = string.digits + string.ascii_uppercase + string.ascii_lowercase  # ASCII order
_BASE = len(DIGITS)


def _index(ch: str) -> int:
    position = DIGITS.find(ch)
    if position < 0:
        raise ValueError(f"invalid rank character {ch!r}")
    return position


def _midpoint(a: str, b: str | None) -> str:
    """Key strictly between a and b; a may be "" (start), b None (end).

    Same approach as the fractional-indexing library: copy the shared prefix
    (padding a with the zero digit), then pick a middle digit or recurse.
    """
    if b is not None:
        n = 0
        while (a[n] if n < len(a) else DIGITS[0]) == b[n]:
            n += 1
        if n > 0:
            return b[:n] + _midpoint(a[n:], b[n:])
    lo = _index(a[0]) if a else 0
    hi = _index(b[0]) if b is not None else _BASE
    if hi - lo > 1:
        return DIGITS[(lo + hi) // 2]
    if b is not None and len(b) > 1:
        return b[:1]
    return DIGITS[lo] + _midpoint(a[1:], None)


# --- integer part: a head letter encodes how many digits follow ---------------------------
# 'a'..'z' are non-negative integers with 1..26 digits, 'A'..'Z' negative ones. "a0" is zero.
# Appending at either end increments the integer, so keys grow logarithmically.

_SMALLEST_INT = "A" + DIGITS[0] * 26


def _int_length(head: str) -> int:
    if "a" <= head <= "z":
        return ord(head) - ord("a") + 2
    if "A" <= head <= "Z":
        return ord("Z") - ord(head) + 2
    raise ValueError(f"invalid rank head {head!r}")


def _int_part(key: str) -> str:
    length = _int_length(key[0])
    if length > len(key):
        raise ValueError(f"invalid rank {key!r}")
    return key[:length]


def _validate(key: str) -> None:
    if key == _SMALLEST_INT:
        raise ValueError(f"invalid rank {key!r}")
    fraction = key[len(_int_part(key)) :]
    for ch in key[1:]:
        _index(ch)
    if fraction.endswith(DIGITS[0]):
        raise ValueError(f"invalid rank {key!r}")


def _increment(x: str) -> str | None:
    head, digits = x[0], list(x[1:])
    for i in reversed(range(len(digits))):
        value = _index(digits[i]) + 1
        if value < _BASE:
            digits[i] = DIGITS[value]
            return head + "".join(digits)
        digits[i] = DIGITS[0]
    if head == "Z":
        return "a" + DIGITS[0]
    if head == "z":
        return None
    new_head = chr(ord(head) + 1)
    if new_head > "a":
        digits.append(DIGITS[0])
    else:
        digits.pop()
    return new_head + "".join(digits)


def _decrement(x: str) -> str | None:
    head, digits = x[0], list(x[1:])
    for i in reversed(range(len(digits))):
        value = _index(digits[i]) - 1
        if value >= 0:
            digits[i] = DIGITS[value]
            return head + "".join(digits)
        digits[i] = DIGITS[-1]
    if head == "a":
        return "Z" + DIGITS[-1]
    if head == "A":
        return None
    new_head = chr(ord(head) - 1)
    if new_head < "Z":
        digits.append(DIGITS[-1])
    else:
        digits.pop()
    return new_head + "".join(digits)


def between(a: str | None, b: str | None) -> str:
    """A key strictly between a and b. None means the start (a) or end (b) of the list."""
    if a is not None:
        _validate(a)
    if b is not None:
        _validate(b)
    if a is not None and b is not None and a >= b:
        raise ValueError(f"rank {a!r} must sort before {b!r}")
    if a is None:
        if b is None:
            return "a" + DIGITS[0]
        int_b = _int_part(b)
        if int_b == _SMALLEST_INT:
            return int_b + _midpoint("", b[len(int_b) :])
        if int_b < b:
            return int_b
        lower = _decrement(int_b)
        if lower is None:  # pragma: no cover - needs 10^46 prepends
            raise ValueError("rank space exhausted")
        return lower
    int_a = _int_part(a)
    frac_a = a[len(int_a) :]
    if b is None:
        higher = _increment(int_a)
        return int_a + _midpoint(frac_a, None) if higher is None else higher
    int_b = _int_part(b)
    if int_a == int_b:
        return int_a + _midpoint(frac_a, b[len(int_b) :])
    higher = _increment(int_a)
    if higher is not None and higher < b:
        return higher
    return int_a + _midpoint(frac_a, None)


def after(a: str | None) -> str:
    return between(a, None)


def before(b: str | None) -> str:
    return between(None, b)
