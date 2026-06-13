import logging
from datetime import datetime
from threading import Lock
from time import monotonic

from infrastructure.config.site_config_manager import get_effective_site_catalog

logger = logging.getLogger(__name__)


class SiteCatalogCache:
    SITE_CATALOG_CACHE_TTL_SECONDS = 30

    def __init__(self):
        self._lock = Lock()
        self._cache: dict[str, dict] | None = None
        self._cache_expires_at: float | None = None

    def get_cached_site_catalog(self) -> dict[str, dict]:
        now_tick = monotonic()
        if (
            self._cache is not None
            and self._cache_expires_at is not None
            and now_tick < self._cache_expires_at
        ):
            return self._cache

        with self._lock:
            now_tick = monotonic()
            if (
                self._cache is not None
                and self._cache_expires_at is not None
                and now_tick < self._cache_expires_at
            ):
                return self._cache

            catalog = get_effective_site_catalog() or {}
            self._cache = catalog
            self._cache_expires_at = now_tick + self.SITE_CATALOG_CACHE_TTL_SECONDS
            return self._cache

    @staticmethod
    def format_datetime(value: datetime | None) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            try:
                return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None


site_catalog_cache = SiteCatalogCache()
get_cached_site_catalog = site_catalog_cache.get_cached_site_catalog
format_datetime = site_catalog_cache.format_datetime
parse_datetime = site_catalog_cache.parse_datetime
