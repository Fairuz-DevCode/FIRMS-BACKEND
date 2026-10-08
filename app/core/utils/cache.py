import time
from typing import Any, Optional

class SimpleCache:
    def __init__(self):
        self._store = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            item, expires_at = self._store[key]
            if time.time() < expires_at:
                return item
            else:
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        expires_at = time.time() + ttl_seconds
        self._store[key] = (value, expires_at)

    def clear(self) -> None:
        self._store.clear()

cache = SimpleCache()
