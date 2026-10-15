import time
from typing import Any, Optional, Dict, Tuple

class SimpleCache:
    """
    In-memory Key-Value cache with TTL support and event-driven invalidation.
    Default TTL is 12 hours (43,200 seconds) for high read-heavy geospatial endpoints.
    """
    def __init__(self, default_ttl: int = 43200):
        self._store: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            item, expires_at = self._store[key]
            if time.time() < expires_at:
                return item
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """
        Purges all cached entries immediately upon data sync/mutation events.
        """
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

cache = SimpleCache()
