from __future__ import annotations

import logging
from urllib.parse import urlparse

from crawl import (
    build_runtime_proxy_config as build_shared_runtime_proxy_config,
)
from crawl import rewrite_playlist_for_proxy

logger = logging.getLogger(__name__)

SITE_SLUG = "javdb"
SITE_DOMAIN = "javdb.com"
DEFAULT_SITE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://javdb.com/",
}
DEFAULT_PROXY_CONFIG = {
    "connect_timeout": 30.0,
    "read_timeout": 180.0,
    "write_timeout": 30.0,
    "pool_timeout": 30.0,
    "chunk_size": 2 * 1024 * 1024,
    "max_retries": 5,
    "max_keepalive_connections": 20,
    "max_connections": 40,
    "keepalive_expiry": 60.0,
    "follow_redirects": True,
    "enable_http2": True,
    "bypass_mode": "mirror",
}


def _requires_cross_host_bypass(target_url: str) -> bool:
    path_lower = str(urlparse(target_url).path or "").strip().lower()
    return path_lower.endswith(".m3u8")


def build_runtime_proxy_config(payload: object | None = None) -> dict[str, object]:
    config = build_shared_runtime_proxy_config(
        site_slug=SITE_SLUG,
        site_domain=SITE_DOMAIN,
        default_site_headers=DEFAULT_SITE_HEADERS,
        default_proxy_config=DEFAULT_PROXY_CONFIG,
        domain=payload,
    )

    if isinstance(payload, dict):
        target_url = str(payload.get("target_url") or "").strip()
        target_host = str(urlparse(target_url).hostname or "").strip().lower()
        if (
            target_host
            and target_host != SITE_DOMAIN
            and not target_host.endswith(f".{SITE_DOMAIN}")
            and _requires_cross_host_bypass(target_url)
        ):
            domain_configs = config.get("domain_configs")
            if isinstance(domain_configs, list) and domain_configs:
                first_config = domain_configs[0]
                if isinstance(first_config, dict):
                    first_config["bypass_domains"] = [target_host]

    return config


def rewrite_proxy_playlist(url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
    return rewrite_playlist_for_proxy(
        url=url,
        content=content,
        site_domain=SITE_DOMAIN,
        referer=referer,
        extensions=("ts", "m4s", "mp4", "jpeg", "jpg", "m3u8"),
    )
