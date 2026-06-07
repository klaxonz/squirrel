"""Helpers for proxy runtime configuration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from .config import get_http_headers, get_proxy_config
from .utils import filter_cookies_to_query_string


def _resolve_runtime_proxy_payload(domain: str | Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    if isinstance(domain, Mapping):
        return (
            str(domain.get('domain') or '').strip().lower() or None,
            str(domain.get('referer') or '').strip() or None,
        )
    return str(domain or '').strip().lower() or None, None


def _apply_runtime_referer_headers(headers: dict[str, str], referer: str | None) -> dict[str, str]:
    effective_referer = str(referer or '').strip()
    if not effective_referer:
        return headers

    updated = dict(headers)
    updated['Referer'] = effective_referer
    parsed = urlparse(effective_referer)
    if parsed.scheme and parsed.netloc:
        updated['Origin'] = f'{parsed.scheme}://{parsed.netloc}'
    return updated


def build_runtime_proxy_config(
    *,
    site_slug: str,
    site_domain: str,
    default_site_headers: Mapping[str, str],
    default_proxy_config: Mapping[str, Any],
    domain: str | Mapping[str, Any] | None = None,
) -> dict[str, object]:
    resolved_domain, referer = _resolve_runtime_proxy_payload(domain)
    effective_domain = resolved_domain or site_domain
    config = dict(default_proxy_config)
    config.update(get_proxy_config(site_slug))
    domain_config = {
        'domain': effective_domain,
        'connect_timeout': float(config['connect_timeout']),
        'read_timeout': float(config['read_timeout']),
        'max_retries': int(config['max_retries']),
        'chunk_size': int(config['chunk_size']),
        'max_connections': int(config['max_connections']),
        'keepalive_expiry': float(config['keepalive_expiry']),
        'enable_http2': bool(config['enable_http2']),
    }
    bypass_mode = str(config.get('bypass_mode') or '').strip().lower()
    if bypass_mode:
        domain_config['bypass_mode'] = bypass_mode

    return {
        'site_headers': _apply_runtime_referer_headers(
            get_http_headers(site_slug, dict(default_site_headers)),
            referer,
        ),
        'domain_configs': [domain_config],
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
    except (OSError, ValueError, TypeError):
        return ''
