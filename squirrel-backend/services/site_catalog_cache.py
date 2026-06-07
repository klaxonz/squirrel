import logging
from datetime import datetime
from threading import Lock
from time import monotonic

from core.site_config_manager import get_effective_site_catalog

logger = logging.getLogger(__name__)

SITE_CATALOG_CACHE_TTL_SECONDS = 30
_site_catalog_cache_lock = Lock()
_site_catalog_cache: dict[str, dict] | None = None
_site_catalog_cache_expires_at_monotonic: float | None = None


def get_cached_site_catalog() -> dict[str, dict]:
    global _site_catalog_cache, _site_catalog_cache_expires_at_monotonic

    now_tick = monotonic()
    if (
        _site_catalog_cache is not None
        and _site_catalog_cache_expires_at_monotonic is not None
        and now_tick < _site_catalog_cache_expires_at_monotonic
    ):
        return _site_catalog_cache

    with _site_catalog_cache_lock:
        now_tick = monotonic()
        if (
            _site_catalog_cache is not None
            and _site_catalog_cache_expires_at_monotonic is not None
            and now_tick < _site_catalog_cache_expires_at_monotonic
        ):
            return _site_catalog_cache

        catalog = get_effective_site_catalog() or {}
        _site_catalog_cache = catalog
        _site_catalog_cache_expires_at_monotonic = now_tick + SITE_CATALOG_CACHE_TTL_SECONDS
        return _site_catalog_cache


def format_datetime(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


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
