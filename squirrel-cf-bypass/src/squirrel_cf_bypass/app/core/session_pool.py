import asyncio
import time

from squirrel_cf_bypass.app.core.models import SessionRecord


class SessionPool:
    def __init__(self, ttl_seconds: float, max_sessions: int):
        self._ttl_seconds = ttl_seconds
        self._max_sessions = max_sessions
        self._items: dict[tuple[str, str | None], SessionRecord] = {}

    @staticmethod
    def _key(hostname: str, proxy: str | None) -> tuple[str, str | None]:
        return hostname.strip().lower(), proxy or None

    def get(self, hostname: str, proxy: str | None):
        record = self._items.get(self._key(hostname, proxy))
        if record is None:
            return None
        if record.created_at + self._ttl_seconds <= time.time():
            self._items.pop(self._key(hostname, proxy), None)
            return None
        return record.session

    def store(self, hostname: str, proxy: str | None, session) -> None:
        if len(self._items) >= self._max_sessions:
            oldest_key = min(self._items, key=lambda key: self._items[key].created_at)
            self._items.pop(oldest_key, None)
        self._items[self._key(hostname, proxy)] = SessionRecord(session=session, created_at=time.time())

    async def clear(self) -> None:
        items = list(self._items.values())
        self._items.clear()
        for record in items:
            close_fn = getattr(record.session, 'close', None)
            if callable(close_fn):
                result = close_fn()
                if asyncio.iscoroutine(result):
                    await result

    def clear_sync(self) -> None:
        asyncio.run(self.clear())

    def size(self) -> int:
        return len(self._items)
