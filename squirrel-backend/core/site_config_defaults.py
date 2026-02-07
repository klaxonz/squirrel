"""Built-in default site configuration values used when catalog entries are missing."""

from __future__ import annotations

from copy import deepcopy


SITE_CONFIG_DEFAULTS = {
    "youtube": {
        "label": "YouTube",
        "domains": ["youtube.com", "youtu.be"],
        "aliases": ["yt"],
        "enabled": True,
        "test_url": "https://www.youtube.com",
        "http": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        },
        "rate_limit": {
            "enabled": True,
            "min_interval": 2.0,
            "max_interval": 5.0,
        },
        "proxy": {
            "connect_timeout": 30.0,
            "read_timeout": 180.0,
            "write_timeout": 30.0,
            "pool_timeout": 30.0,
            "keepalive_expiry": 60.0,
            "max_connections": 100,
            "max_keepalive_connections": 50,
            "chunk_size": 2 * 1024 * 1024,
            "max_retries": 5,
            "enable_http2": True,
            "follow_redirects": True,
        },
        "login": {
            "check_url": "https://www.youtube.com/feed/channels",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "timeout": 20.0,
        },
    },
    "bilibili": {
        "label": "Bilibili",
        "domains": ["bilibili.com", "b23.tv"],
        "aliases": ["bili"],
        "enabled": True,
        "test_url": "https://www.bilibili.com",
        "http": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
                "Referer": "https://www.bilibili.com",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            }
        },
        "rate_limit": {
            "enabled": True,
            "min_interval": 3.0,
            "max_interval": 5.0,
        },
        "proxy": {
            "connect_timeout": 30.0,
            "read_timeout": 120.0,
            "write_timeout": 30.0,
            "pool_timeout": 30.0,
            "keepalive_expiry": 30.0,
            "max_connections": 50,
            "max_keepalive_connections": 50,
            "chunk_size": 2 * 1024 * 1024,
            "max_retries": 5,
            "enable_http2": True,
            "follow_redirects": True,
        },
        "login": {
            "check_url": "https://api.bilibili.com/x/web-interface/nav",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
            },
            "timeout": 15.0,
        },
        "metadata": {
            "requires_cookies": True,
        },
    },
    "pornhub": {
        "label": "Pornhub",
        "domains": ["pornhub.com"],
        "aliases": ["ph"],
        "enabled": True,
        "test_url": "https://www.pornhub.com",
        "http": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.pornhub.com",
            }
        },
        "rate_limit": {
            "enabled": True,
            "min_interval": 3.0,
            "max_interval": 8.0,
        },
        "proxy": {
            "connect_timeout": 30.0,
            "read_timeout": 180.0,
            "write_timeout": 30.0,
            "pool_timeout": 30.0,
            "keepalive_expiry": 60.0,
            "max_connections": 40,
            "max_keepalive_connections": 20,
            "chunk_size": 2 * 1024 * 1024,
            "max_retries": 5,
            "enable_http2": True,
            "follow_redirects": True,
        },
        "login": {
            "check_url": "https://www.pornhub.com/",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "timeout": 20.0,
        },
        "metadata": {
            "nsfw": True,
            "requires_cookies": True,
        },
    },
    "javdb": {
        "label": "JavDB",
        "domains": ["javdb.com"],
        "aliases": [],
        "enabled": True,
        "test_url": "https://javdb.com",
        "http": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        },
        "rate_limit": {
            "enabled": True,
            "min_interval": 5.0,
            "max_interval": 8.0,
        },
        "proxy": {
            "connect_timeout": 30.0,
            "read_timeout": 180.0,
            "write_timeout": 30.0,
            "pool_timeout": 30.0,
            "keepalive_expiry": 60.0,
            "max_connections": 40,
            "max_keepalive_connections": 20,
            "chunk_size": 2 * 1024 * 1024,
            "max_retries": 5,
            "enable_http2": True,
            "follow_redirects": True,
        },
        "login": {
            "check_url": "https://javdb.com/users/collection_actors",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            },
            "timeout": 15.0,
        },
        "metadata": {
            "requires_cookies": True,
            "requires_login": True,
            "nsfw": True,
        },
    },
}


def get_default_site_config(slug: str) -> dict:
    config = SITE_CONFIG_DEFAULTS.get(slug.lower())
    return deepcopy(config) if config else {}
