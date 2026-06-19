"""Utilities for applying site catalog overrides to runtime components."""

from __future__ import annotations

from copy import copy
from typing import Any

from crawl import configure_rate_limit as configure_crawl_rate_limit
from crawl import configure_rate_limit_enabled as configure_crawl_rate_limit_enabled

from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.runtime_config import set_site_configs
from shared_kernel.infrastructure.rate_limiter import rate_limiter as backend_rate_limiter


def _deep_merge(base: dict, overrides: dict) -> dict:
    result = copy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def build_plugin_site_catalog() -> dict[str, dict]:
    return SiteCatalog.build_plugin_site_catalog()


def get_effective_site_catalog(stored_catalog: dict[str, dict] | None = None) -> dict[str, dict]:
    overrides = stored_catalog if stored_catalog is not None else (SiteCatalog.load_override_catalog() or {})
    effective: dict[str, dict] = {slug: copy(defaults) for slug, defaults in build_plugin_site_catalog().items()}

    for slug, override in (overrides or {}).items():
        if slug not in effective:
            continue
        effective[slug] = _deep_merge(effective[slug], override)

    return effective


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'y', 'on'}:
        return True
    if text in {'false', '0', 'no', 'n', 'off'}:
        return False
    return default


def _iter_rate_limit_entries(effective_catalog: dict[str, dict]):
    for info in effective_catalog.values():
        rate_limit = info.get('rate_limit') or {}
        rate_limit_enabled = _parse_bool(rate_limit.get('enabled'), True)
        min_interval = rate_limit.get('min_interval')
        max_interval = rate_limit.get('max_interval')
        min_value: float | None = None
        max_value: float | None = None
        if min_interval not in (None, '') and max_interval not in (None, ''):
            try:
                min_value = float(min_interval)
                max_value = float(max_interval)
            except (TypeError, ValueError):
                min_value = None
                max_value = None

        for domain in info.get('domains', []) or []:
            if domain:
                yield domain, rate_limit_enabled, min_value, max_value


def apply_crawl_rate_limit_overrides(catalog: dict[str, dict] | None = None) -> None:
    """Apply site rate limits to the shared runtime helpers used by plugin processes."""
    effective_catalog = get_effective_site_catalog(catalog)

    for domain, rate_limit_enabled, min_value, max_value in _iter_rate_limit_entries(effective_catalog):
        try:
            configure_crawl_rate_limit_enabled(domain, rate_limit_enabled)
            if not rate_limit_enabled:
                continue
            if min_value is None or max_value is None:
                continue
            configure_crawl_rate_limit(domain, min_value, max_value)
        except (TypeError, ValueError, AttributeError):
            continue


def apply_site_config_overrides(catalog: dict[str, dict] | None = None) -> None:
    """Apply the current site catalog to backend-owned runtime state."""
    effective_catalog = get_effective_site_catalog(catalog)

    set_site_configs(effective_catalog)
    apply_crawl_rate_limit_overrides(effective_catalog)

    for domain, rate_limit_enabled, min_value, max_value in _iter_rate_limit_entries(effective_catalog):
        try:
            backend_rate_limiter.set_domain_enabled(domain, rate_limit_enabled)
            if not rate_limit_enabled:
                continue
            if min_value is None or max_value is None:
                continue
            backend_rate_limiter.add_rate_limit(domain, min_value, max_value)
        except (TypeError, ValueError, AttributeError):
            continue
