"""Lightweight sliding-window rate limiter protecting authentication endpoints."""

from collections import defaultdict, deque
import time

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AppError

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limiter() -> None:
    """Clear in-memory rate-limit counters (used by test isolation)."""
    _BUCKETS.clear()


def enforce_auth_rate_limit(request: Request) -> None:
    """Apply sliding-window per-client throttling on auth endpoints when enabled."""
    settings = get_settings()
    if not settings.auth_rate_limit_enabled:
        return

    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    now = time.monotonic()
    window_sec = settings.auth_rate_limit_window_sec
    max_requests = settings.auth_rate_limit_max_requests

    bucket = _BUCKETS[key]
    cutoff = now - window_sec
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()

    if len(bucket) >= max_requests:
        raise AppError(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Too many requests. Please wait a minute before trying again.",
        )

    bucket.append(now)
