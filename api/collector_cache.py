"""Small in-memory TTL cache for collector results."""

from datetime import datetime, timedelta
from threading import Lock
from typing import Any


class MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._expiry: dict[str, datetime] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            expiry = self._expiry.get(key)
            if expiry is None or datetime.now() >= expiry:
                return None
            return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = value
            self._expiry[key] = datetime.now() + timedelta(seconds=max(ttl_seconds, 1))

    def get_fallback(self, key: str) -> Any | None:
        """Return the last value even when its TTL has elapsed."""
        with self._lock:
            return self._store.get(key)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._expiry.clear()
