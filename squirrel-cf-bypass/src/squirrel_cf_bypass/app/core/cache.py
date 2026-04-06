import time

from squirrel_cf_bypass.app.core.models import ClearanceRecord


class ClearanceCache:
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._items: dict[tuple[str, str | None], ClearanceRecord] = {}

    @staticmethod
    def _key(hostname: str, proxy: str | None) -> tuple[str, str | None]:
        return hostname.strip().lower(), proxy or None

    def get(self, hostname: str, proxy: str | None) -> ClearanceRecord | None:
        record = self._items.get(self._key(hostname, proxy))
        if record is None:
            return None
        if record.expires_at <= time.time():
            self._items.pop(self._key(hostname, proxy), None)
            return None
        return record

    def set(self, hostname: str, proxy: str | None, record: ClearanceRecord) -> None:
        self._items[self._key(hostname, proxy)] = record

    def invalidate(self, hostname: str, proxy: str | None) -> None:
        self._items.pop(self._key(hostname, proxy), None)

    def clear(self) -> None:
        self._items.clear()

    def size(self) -> int:
        return len(self._items)
