from __future__ import annotations

from collections.abc import Callable

_cloudflare_bypass_client: object | None = None


def set_cloudflare_bypass_client(client: object | None) -> None:
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client
    if client is None:
        return

    from crawl import configure_cloudflare_bypass_client

    configure_cloudflare_bypass_client(client)


def get_cloudflare_bypass_client() -> object | None:
    return _cloudflare_bypass_client


def set_cookie_file_resolver(resolver: Callable[[str], str | None] | None) -> None:
    if resolver is None:
        return

    from crawl import configure_cookie_file_resolver

    configure_cookie_file_resolver(resolver)


def set_cookie_domain_resolver(resolver: Callable[[str], str] | None) -> None:
    if resolver is None:
        return

    from crawl import configure_cookie_domain_resolver

    configure_cookie_domain_resolver(resolver)


def reset_runtime_http_state() -> None:
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = None

    from crawl import http as crawl_http
    from crawl import utils as crawl_utils

    crawl_http._cloudflare_bypass_client = None
    crawl_utils._cookie_file_resolver = None
    crawl_utils._cookie_domain_resolver = None
