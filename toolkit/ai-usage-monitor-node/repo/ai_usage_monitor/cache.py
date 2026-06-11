"""Tiny in-process TTL cache.

Used to decouple the display/refresh cadence from how often we actually hit
rate-limited network endpoints (Cursor dashboard RPC, Claude OAuth usage). The
UI can redraw every few seconds while these calls are served from cache until
the TTL elapses.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

_T = TypeVar("_T")

_store: dict[str, tuple[float, object]] = {}


def cached(key: str, ttl: float, producer: Callable[[], _T]) -> _T:
    """Return a cached value for `key` if fresh, else call `producer`.

    Only successful (non-raising) results are cached. A non-positive ttl
    disables caching.
    """
    now = time.monotonic()
    if ttl > 0:
        hit = _store.get(key)
        if hit is not None and (now - hit[0]) < ttl:
            return hit[1]  # type: ignore[return-value]
    value = producer()
    if ttl > 0:
        _store[key] = (now, value)
    return value


def invalidate(key: str | None = None) -> None:
    """Drop one or all cache entries (used to force a hard refresh)."""
    if key is None:
        _store.clear()
    else:
        _store.pop(key, None)
