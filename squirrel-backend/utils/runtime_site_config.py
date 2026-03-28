from __future__ import annotations

from typing import Optional


SiteConfig = dict[str, dict]

_site_configs: SiteConfig = {}


def _normalize_slug(slug: Optional[str]) -> str | None:
    if slug is None:
        return None
    clean = str(slug).strip().lower()
    return clean or None


def reset_runtime_site_state() -> None:
    _site_configs.clear()


def set_site_configs(configs: Optional[dict]) -> None:
    reset_runtime_site_state()
    for slug, config in (configs or {}).items():
        normalized = _normalize_slug(slug)
        if normalized:
            _site_configs[normalized] = dict(config or {})


def get_site_config(slug: Optional[str]) -> dict:
    normalized = _normalize_slug(slug)
    if not normalized:
        return {}
    return _site_configs.get(normalized, {})


def _merge_headers(base: Optional[dict[str, str]], overrides: Optional[dict[str, str]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if base:
        headers.update({str(key): str(value) for key, value in base.items() if value is not None})
    if overrides:
        headers.update({str(key): str(value) for key, value in overrides.items() if value is not None})
    return headers


def get_http_headers(slug: str, base: Optional[dict[str, str]] = None) -> dict[str, str]:
    config = get_site_config(slug).get('http') or {}
    return _merge_headers(base, config.get('headers'))


def get_login_config(slug: str) -> dict:
    return get_site_config(slug).get('login') or {}


def get_login_headers(slug: str, base: Optional[dict[str, str]] = None) -> dict[str, str]:
    config = get_login_config(slug)
    headers_override = config.get('headers') if isinstance(config, dict) else None
    http_headers = get_http_headers(slug)
    headers = _merge_headers(http_headers, headers_override)
    return _merge_headers(base, headers)


def get_proxy_config(slug: str) -> dict:
    return get_site_config(slug).get('proxy') or {}


def get_rate_limit_config(slug: str) -> dict:
    return get_site_config(slug).get('rate_limit') or {}
