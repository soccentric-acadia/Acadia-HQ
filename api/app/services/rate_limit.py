"""In-process sliding-window rate limiter (T-P34, HQ-012).

Keyed by the direct client address (never X-Forwarded-For, which the client
controls). Per-process: with several API workers each enforces its own
budget, which still bounds brute force; a shared limiter would sit in Redis.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_WINDOW_S = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def check(bucket: str, request: Request, per_minute: int) -> None:
    key = f"{bucket}:{request.client.host if request.client else 'unknown'}"
    now = time.monotonic()
    window = _hits[key]
    while window and now - window[0] > _WINDOW_S:
        window.popleft()
    if len(window) >= per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too many requests",
            headers={"Retry-After": str(int(_WINDOW_S - (now - window[0])) + 1)},
        )
    window.append(now)


def reset() -> None:
    """Tests only."""
    _hits.clear()
