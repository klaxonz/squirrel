"""Helpers for proxy runtime configuration."""
from __future__ import annotations

from typing import Any, Mapping

from .config import get_http_headers, get_proxy_config
from .utils import filter_cookies_to_query_string


def build_runtime_proxy_config(
    *,
    site_slug: str,
    site_domain: str,
    default_site_headers: Mapping[str, str],
    default_proxy_config: Mapping[str, Any],
    domain: str | None = None,
) -> dict[str, object]:
    effective_domain = str(domain or site_domain).strip().lower() or site_domain
    config = dict(default_proxy_config)
    config.update(get_proxy_config(site_slug))
    return {
        'site_headers': get_http_headers(site_slug, dict(default_site_headers)),
        'domain_configs': [{
            'domain': effective_domain,
            'connect_timeout': float(config['connect_timeout']),
            'read_timeout': float(config['read_timeout']),
            'max_retries': int(config['max_retries']),
            'chunk_size': int(config['chunk_size']),
            'max_connections': int(config['max_connections']),
            'keepalive_expiry': float(config['keepalive_expiry']),
            'enable_http2': bool(config['enable_http2']),
        }],
    }


def build_proxy_config_values(site_slug: str, default_proxy_config: Mapping[str, Any]) -> dict[str, Any]:
    config = dict(default_proxy_config)
    config.update(get_proxy_config(site_slug))
    return config


def safe_cookie_header_value(domain_or_url: str) -> str:
    if not domain_or_url:
        return ''

    target = domain_or_url
    if '://' not in target:
        target = f'https://{str(domain_or_url).lstrip(".")}'

    try:
        return filter_cookies_to_query_string(target)
    except Exception:
        return ''
