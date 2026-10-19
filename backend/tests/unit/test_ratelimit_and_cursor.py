from datetime import UTC, datetime

import pytest

from radicle.api.pagination import decode_cursor, encode_cursor
from radicle.api.ratelimit import SlidingWindowLimiter
from radicle.core.errors import RateLimited, ValidationFailed


def test_limiter_blocks_after_limit_and_is_per_key() -> None:
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        limiter.hit("a", 3)
    with pytest.raises(RateLimited) as exc:
        limiter.hit("a", 3)
    assert exc.value.headers and int(exc.value.headers["Retry-After"]) >= 1
    limiter.hit("b", 3)


def test_limiter_window_expires() -> None:
    limiter = SlidingWindowLimiter(window_seconds=0)
    for _ in range(5):
        limiter.hit("a", 1)


def test_cursor_roundtrip() -> None:
    ts = datetime(2026, 10, 18, 15, 2, 11, tzinfo=UTC)
    assert decode_cursor(encode_cursor(ts, "abc")) == (ts, "abc")
    assert decode_cursor(None) is None


@pytest.mark.parametrize("bad", ["!!!", "bm90LWpzb24", "WzFd"])
def test_invalid_cursor(bad: str) -> None:
    with pytest.raises(ValidationFailed, match="Invalid cursor"):
        decode_cursor(bad)
