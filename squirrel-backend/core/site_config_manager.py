"""Utilities for applying site catalog overrides to runtime components."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Any

from crawl import configure_rate_limit, configure_rate_limit_enabled, set_site_configs
from utils.rate_limiter import rate_limiter as backend_rate_limiter
from utils.site_catalog import SiteCatalog
from .site_config_defaults import SITE_CONFIG_DEFAULTS


def _deep_merge(base: dict, overrides: dict) -> dict:
    result = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def get_effective_site_catalog(stored_catalog: Dict[str, dict] | None = None) -> Dict[str, dict]:
    stored_catalog = stored_catalog or SiteCatalog.get_catalog() or {}
    effective: Dict[str, dict] = {}

    for slug, defaults in SITE_CONFIG_DEFAULTS.items():
        effective[slug] = deepcopy(defaults)

    for slug, overrides in stored_catalog.items():
        if slug in effective:
            effective[slug] = _deep_merge(effective[slug], overrides)
        else:
            effective[slug] = deepcopy(overrides)

    return effective


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def apply_site_config_overrides(catalog: Dict[str, dict] | None = None) -> None:
    """Apply the current site catalog to the shared SDK configuration."""
    effective_catalog = get_effective_site_catalog(catalog)

    set_site_configs(effective_catalog)

    for info in effective_catalog.values():
        rate_limit = info.get("rate_limit") or {}
        rate_limit_enabled = _parse_bool(rate_limit.get("enabled"), True)
        min_interval = rate_limit.get("min_interval")
        max_interval = rate_limit.get("max_interval")
        min_value: float | None = None
        max_value: float | None = None
        if min_interval not in (None, "") and max_interval not in (None, ""):
            try:
                min_value = float(min_interval)
                max_value = float(max_interval)
            except (TypeError, ValueError):
                min_value = None
                max_value = None

        for domain in info.get("domains", []) or []:
            if not domain:
                continue
            try:
                configure_rate_limit_enabled(domain, rate_limit_enabled)
                backend_rate_limiter.set_domain_enabled(domain, rate_limit_enabled)
                if not rate_limit_enabled:
                    continue
                if min_value is None or max_value is None:
                    continue
                configure_rate_limit(domain, min_value, max_value)
                backend_rate_limiter.add_rate_limit(domain, min_value, max_value)
            except Exception:
                continue
