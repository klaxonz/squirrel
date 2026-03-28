from __future__ import annotations

from typing import Callable, Optional

_cloudflare_bypass_client: object | None = None
_cookie_file_resolver: Optional[Callable[[str], Optional[str]]] = None


def set_cloudflare_bypass_client(client: object | None) -> None:
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client
    try:
        from crawl import configure_cloudflare_bypass_client

        if client is not None:
            configure_cloudflare_bypass_client(client)
    except Exception:
        pass


def get_cloudflare_bypass_client() -> object | None:
    return _cloudflare_bypass_client


def set_cookie_file_resolver(resolver: Optional[Callable[[str], Optional[str]]]) -> None:
    global _cookie_file_resolver
    _cookie_file_resolver = resolver
    try:
        from crawl import configure_cookie_file_resolver

        if resolver is not None:
            configure_cookie_file_resolver(resolver)
    except Exception:
        pass


def get_cookie_file_resolver() -> Optional[Callable[[str], Optional[str]]]:
    return _cookie_file_resolver


def reset_runtime_http_state() -> None:
    global _cloudflare_bypass_client, _cookie_file_resolver

    _cloudflare_bypass_client = None
    _cookie_file_resolver = None

    try:
        from crawl import http as crawl_http

        crawl_http._cloudflare_bypass_client = None
    except Exception:
        pass

    try:
        from crawl import utils as crawl_utils

        crawl_utils._cookie_file_resolver = None
    except Exception:
        pass
