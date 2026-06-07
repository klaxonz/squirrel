from __future__ import annotations

import logging

from crawl import (
    build_runtime_proxy_config as build_shared_runtime_proxy_config,
)
from crawl import rewrite_playlist_for_proxy

logger = logging.getLogger(__name__)

SITE_SLUG = 'youporn'
SITE_DOMAIN = 'youporn.com'
DEFAULT_SITE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://www.youporn.com/',
    'Origin': 'https://www.youporn.com',
    'Accept-Language': 'en-US,en;q=0.9',
}
DEFAULT_PROXY_CONFIG = {
    'connect_timeout': 30.0,
    'read_timeout': 180.0,
    'write_timeout': 30.0,
    'pool_timeout': 30.0,
    'chunk_size': 2 * 1024 * 1024,
    'max_retries': 5,
    'max_keepalive_connections': 20,
    'max_connections': 40,
    'keepalive_expiry': 60.0,
    'follow_redirects': True,
    'enable_http2': True,
}


def build_runtime_proxy_config(payload: object | None = None) -> dict[str, object]:
    return build_shared_runtime_proxy_config(
        site_slug=SITE_SLUG,
        site_domain=SITE_DOMAIN,
        default_site_headers=DEFAULT_SITE_HEADERS,
        default_proxy_config=DEFAULT_PROXY_CONFIG,
        domain=payload,
    )


def rewrite_proxy_playlist(url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
    return rewrite_playlist_for_proxy(
        url=url,
        content=content,
        site_domain=SITE_DOMAIN,
        referer=referer,
        extensions=('ts', 'm4s', 'mp4', 'jpeg', 'jpg', 'm3u8'),
    )
