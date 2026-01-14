"""
In-Memory LRU Cache Service.

Lightweight caching layer to reduce external calls.
Survives across warm Lambda invocations.
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, datetime]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl_seconds):
                del self._cache[key]
                return None

            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, datetime.utcnow())

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
            }
