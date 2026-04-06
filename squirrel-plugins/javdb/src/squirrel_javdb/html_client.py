from __future__ import annotations

import logging
from urllib.parse import urlparse

from crawl import (
    filter_cookies_to_query_string,
    get_http_headers,
    get_login_headers,
    request,
    request_without_limit,
)

logger = logging.getLogger(__name__)

SITE_SLUG = 'javdb'
DEFAULT_JAVDB_TIMEOUT_SECONDS = 30.0
_BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
}


def build_javdb_headers(url: str, *, login: bool = False) -> dict[str, str]:
    header_builder = get_login_headers if login else get_http_headers
    headers = header_builder(SITE_SLUG, _BASE_HEADERS)

    cookies = filter_cookies_to_query_string(url)
    if cookies:
        headers['Cookie'] = cookies

    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        origin = f'{parsed.scheme}://{parsed.netloc}'
        headers.setdefault('Referer', origin + '/')
        headers.setdefault('Origin', origin)

    return headers


def fetch_javdb_html(
    url: str,
    *,
    login: bool = False,
    timeout: float = DEFAULT_JAVDB_TIMEOUT_SECONDS,
    allow_redirects: bool = True,
    use_rate_limit: bool = True,
):
    headers = build_javdb_headers(url, login=login)
    requester = request if use_rate_limit else request_without_limit
    kwargs = {
        'headers': headers,
        'timeout': timeout,
        'allow_redirects': allow_redirects,
    }

    try:
        return requester('GET', url, bypass_mode='html', **kwargs)
    except Exception as exc:
        logger.debug('JavDB bypass request failed for %s: %s', url, exc, exc_info=True)
        return requester('GET', url, **kwargs)
