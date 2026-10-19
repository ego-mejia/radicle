"""In-process sliding-window limiter. Enough for the single-process deployment of stage 1."""

import math
import time
from collections import defaultdict, deque

from radicle.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, math.ceil(self.window - (now - hits[0])))
            raise RateLimited(
                f"Too many attempts. Try again in {retry_after} seconds.",
                extra={"retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


login_limiter = SlidingWindowLimiter()
