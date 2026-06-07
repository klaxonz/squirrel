from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse, urlunparse

from crawl import (
    build_runtime_proxy_config as build_shared_runtime_proxy_config,
)
from crawl import rewrite_playlist_for_proxy

logger = logging.getLogger(__name__)

SITE_SLUG = 'youtube'
SITE_DOMAIN = 'youtube.com'
YOUTUBE_MWEB_USER_AGENT = (
    'Mozilla/5.0 (iPad; CPU OS 16_7_10 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
)
DEFAULT_SITE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://www.youtube.com',
    'Accept': '*/*',
}
DEFAULT_PROXY_CONFIG = {
    'connect_timeout': 30.0,
    'read_timeout': 180.0,
    'write_timeout': 30.0,
    'pool_timeout': 30.0,
    'chunk_size': 2 * 1024 * 1024,
    'max_retries': 5,
    'max_keepalive_connections': 50,
    'max_connections': 100,
    'keepalive_expiry': 60.0,
    'follow_redirects': True,
    'enable_http2': True,
}


def _normalize_proxy_payload(payload: object | None) -> tuple[object | None, str | None, str | None]:
    if isinstance(payload, dict):
        return (
            payload,
            str(payload.get('target_url') or '').strip() or None,
            str(payload.get('referer') or '').strip() or None,
        )
    return payload, None, None


def _apply_youtube_upstream_overrides(
    headers: dict[str, str],
    target_url: str | None,
    referer: str | None,
) -> dict[str, str]:
    if not target_url:
        return headers

    parsed = urlparse(target_url)
    host = str(parsed.hostname or '').lower()
    if not host.endswith('googlevideo.com'):
        return headers

    client_name = str((parse_qs(parsed.query).get('c') or [''])[0]).upper()
    if client_name != 'MWEB':
        return headers

    updated = dict(headers)
    updated['User-Agent'] = YOUTUBE_MWEB_USER_AGENT

    effective_referer = str(referer or updated.get('Referer') or '').strip()
    if effective_referer:
        referer_parts = urlparse(effective_referer)
        if referer_parts.scheme and referer_parts.netloc:
            updated['Referer'] = urlunparse(
                (
                    referer_parts.scheme,
                    'm.youtube.com',
                    referer_parts.path,
                    referer_parts.params,
                    referer_parts.query,
                    referer_parts.fragment,
                )
            )
            updated['Origin'] = 'https://m.youtube.com'
            return updated

    updated['Referer'] = 'https://m.youtube.com/'
    updated['Origin'] = 'https://m.youtube.com'
    return updated


def build_runtime_proxy_config(payload: object | None = None) -> dict[str, object]:
    resolved_payload, target_url, referer = _normalize_proxy_payload(payload)
    config = build_shared_runtime_proxy_config(
        site_slug=SITE_SLUG,
        site_domain=SITE_DOMAIN,
        default_site_headers=DEFAULT_SITE_HEADERS,
        default_proxy_config=DEFAULT_PROXY_CONFIG,
        domain=resolved_payload,
    )
    config['site_headers'] = _apply_youtube_upstream_overrides(
        dict(config.get('site_headers') or {}),
        target_url,
        referer,
    )
    return config


def rewrite_proxy_playlist(url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
    return rewrite_playlist_for_proxy(
        url=url,
        content=content,
        site_domain=SITE_DOMAIN,
        referer=referer,
        extensions=('ts', 'm4s', 'mp4', 'm3u8', 'jpg', 'jpeg', 'vtt'),
    )
