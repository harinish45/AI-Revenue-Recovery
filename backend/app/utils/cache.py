import time


class TTLCache:
    """In-memory cache for read-heavy endpoints that can tolerate a few seconds of staleness."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}

    def get_or_set(self, key: str, compute):
        cached = self._store.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < self._ttl:
            return cached[1]
        value = compute()
        self._store[key] = (now, value)
        return value

    def invalidate(self, key: str = None):
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)
