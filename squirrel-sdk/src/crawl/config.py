"""Runtime site configuration overrides shared between backend and plugins."""

from __future__ import annotations

SiteConfig = dict[str, dict]


_site_configs: SiteConfig = {}


def _normalize_slug(slug: str | None) -> str | None:
    if slug is None:
        return None
    clean = str(slug).strip().lower()
    return clean or None


def set_site_config(slug: str, config: dict | None) -> None:
    """Register/override a single site configuration."""
    normalized = _normalize_slug(slug)
    if not normalized:
        return
    _site_configs[normalized] = dict(config or {})


def set_site_configs(configs: dict | None) -> None:
    """Replace all site configs at once."""
    _site_configs.clear()
    for slug, cfg in (configs or {}).items():
        set_site_config(slug, cfg or {})


def get_site_config(slug: str | None) -> dict:
    normalized = _normalize_slug(slug)
    if not normalized:
        return {}
    return _site_configs.get(normalized, {})


def _merge_headers(base: dict[str, str] | None, overrides: dict[str, str] | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if base:
        headers.update({str(k): str(v) for k, v in base.items() if v is not None})
    if overrides:
        headers.update({str(k): str(v) for k, v in overrides.items() if v is not None})
    return headers


def get_http_headers(slug: str, base: dict[str, str] | None = None) -> dict[str, str]:
    """Return merged HTTP headers using the site's overrides."""
    config = get_site_config(slug).get("http") or {}
    return _merge_headers(base, config.get("headers"))


def get_login_config(slug: str) -> dict:
    return get_site_config(slug).get("login") or {}


def get_login_headers(slug: str, base: dict[str, str] | None = None) -> dict[str, str]:
    config = get_login_config(slug)
    headers_override = config.get("headers") if isinstance(config, dict) else None
    # login headers should build on top of default HTTP headers as well
    http_headers = get_http_headers(slug)
    headers = _merge_headers(http_headers, headers_override)
    return _merge_headers(base, headers)


def get_proxy_config(slug: str) -> dict:
    return get_site_config(slug).get("proxy") or {}


def get_rate_limit_config(slug: str) -> dict:
    return get_site_config(slug).get("rate_limit") or {}

