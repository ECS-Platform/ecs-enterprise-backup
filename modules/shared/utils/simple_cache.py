"""Lightweight, dependency-free in-process caching for ECS.

A tiny TTL cache built for the audit-intelligence read paths (mapping catalog
derivation, dashboard summaries). It intentionally avoids Redis / external
services: everything lives in the current process and is safe for the demo, the
test suite, and single-process deployments.

Design goals
------------
* **Safe by default** — every cached entry has a TTL so stale data self-expires;
  a hard ``maxsize`` bounds memory so a cache can never grow without limit.
* **Thread-safe** — a single lock guards each cache (FastAPI/Starlette runs
  request handlers on a threadpool for sync endpoints).
* **Test-friendly** — every cache registers itself, so :func:`reset_all_caches`
  clears the whole process in one call (use in fixtures). Individual caches also
  expose ``.clear()``.
* **Never raises for the caller** — a cache miss simply recomputes; caching is a
  pure optimisation and must never change correctness.

Typical use::

    from modules.shared.utils.simple_cache import cached

    @cached(ttl_seconds=300, maxsize=1)
    def expensive_catalog() -> dict:
        ...

    # In tests:
    from modules.shared.utils.simple_cache import reset_all_caches
    reset_all_caches()
"""

from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable, Hashable

__all__ = [
    "TTLCache",
    "cached",
    "register_cache",
    "reset_all_caches",
    "cache_registry_size",
]

#: Default time-to-live for cached entries (5 minutes). Chosen so demo/read
#: dashboards feel instant without ever serving badly stale data.
DEFAULT_TTL_SECONDS = 300

#: Default hard cap on distinct cached keys per cache. Bounds memory so a hostile
#: or buggy caller cannot blow up the process by varying arguments.
DEFAULT_MAXSIZE = 256


# --------------------------------------------------------------------------- #
# Global registry (so tests / admin hooks can reset every cache at once)
# --------------------------------------------------------------------------- #
_REGISTRY: "list[TTLCache]" = []
_REGISTRY_LOCK = threading.Lock()


def register_cache(cache: "TTLCache") -> None:
    """Register a cache so :func:`reset_all_caches` can clear it."""
    with _REGISTRY_LOCK:
        _REGISTRY.append(cache)


def reset_all_caches() -> None:
    """Clear every registered cache. Idempotent; safe to call in test fixtures."""
    with _REGISTRY_LOCK:
        caches = list(_REGISTRY)
    for cache in caches:
        cache.clear()


def cache_registry_size() -> int:
    """Number of registered caches (diagnostic / test helper)."""
    with _REGISTRY_LOCK:
        return len(_REGISTRY)


# --------------------------------------------------------------------------- #
# TTL cache
# --------------------------------------------------------------------------- #
class TTLCache:
    """A minimal thread-safe TTL cache with a bounded size.

    Keys must be hashable. Entries expire ``ttl_seconds`` after insertion. When
    the cache is full a single expired-or-oldest entry is evicted to make room
    (approximate LRU — good enough for the small, low-cardinality catalogs here).
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        maxsize: int = DEFAULT_MAXSIZE,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.maxsize = max(1, int(maxsize))
        self._time = time_func
        self._lock = threading.Lock()
        #: key -> (expires_at, value)
        self._store: dict[Hashable, tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0
        register_cache(self)

    # -- core ------------------------------------------------------------- #
    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return a live cached value or ``default`` (also counts hit/miss)."""
        now = self._time()
        with self._lock:
            entry = self._store.get(key)
            if entry is not None and entry[0] > now:
                self.hits += 1
                return entry[1]
            if entry is not None:  # expired -> drop it
                self._store.pop(key, None)
            self.misses += 1
            return default

    def set(self, key: Hashable, value: Any) -> None:
        now = self._time()
        with self._lock:
            if key not in self._store and len(self._store) >= self.maxsize:
                self._evict_one_locked(now)
            self._store[key] = (now + self.ttl_seconds, value)

    def get_or_set(self, key: Hashable, factory: Callable[[], Any]) -> Any:
        """Return the cached value for *key*, computing + storing it on a miss.

        The factory is called OUTSIDE the lock so a slow computation never blocks
        other cache users. A benign race (two callers compute concurrently on a
        cold key) only wastes a little work and is safe for pure/deterministic
        factories, which is all we cache.
        """
        sentinel = object()
        found = self.get(key, sentinel)
        if found is not sentinel:
            return found
        value = factory()
        self.set(key, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    # -- introspection ---------------------------------------------------- #
    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._store),
                "maxsize": self.maxsize,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    # -- internals -------------------------------------------------------- #
    def _evict_one_locked(self, now: float) -> None:
        """Drop one entry (prefer an expired one, else the soonest to expire)."""
        oldest_key: Hashable | None = None
        oldest_expiry = float("inf")
        for k, (expires_at, _v) in self._store.items():
            if expires_at <= now:  # found an expired entry -> evict immediately
                self._store.pop(k, None)
                return
            if expires_at < oldest_expiry:
                oldest_expiry = expires_at
                oldest_key = k
        if oldest_key is not None:
            self._store.pop(oldest_key, None)


# --------------------------------------------------------------------------- #
# Decorator
# --------------------------------------------------------------------------- #
def _make_key(args: tuple, kwargs: dict) -> Hashable:
    """Build a hashable cache key from positional + keyword args.

    Falls back to the string repr for unhashable arguments so decorating never
    raises; callers with exotic args just get a stable-but-coarser key.
    """
    if not args and not kwargs:
        return "()"
    try:
        key_parts: tuple = args
        if kwargs:
            key_parts = key_parts + tuple(sorted(kwargs.items()))
        hash(key_parts)  # validate hashability
        return key_parts
    except TypeError:
        return repr((args, tuple(sorted(kwargs.items()))))


def cached(
    *,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    maxsize: int = DEFAULT_MAXSIZE,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Memoize a function's return value in a process-local :class:`TTLCache`.

    The wrapper exposes ``.cache`` (the underlying :class:`TTLCache`) and
    ``.cache_clear()`` so callers/tests can inspect or reset it directly, mirroring
    :func:`functools.lru_cache` ergonomics while adding a TTL and a global reset.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        cache = TTLCache(ttl_seconds=ttl_seconds, maxsize=maxsize)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _make_key(args, kwargs)
            return cache.get_or_set(key, lambda: fn(*args, **kwargs))

        wrapper.cache = cache  # type: ignore[attr-defined]
        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        wrapper.cache_stats = cache.stats  # type: ignore[attr-defined]
        return wrapper

    return decorator
