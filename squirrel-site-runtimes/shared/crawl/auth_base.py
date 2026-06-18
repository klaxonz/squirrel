from __future__ import annotations

import logging
from collections.abc import Callable

import httpx

from .config import get_login_config, get_login_headers
from .core import LoginStatusResult
from .http import request_without_limit
from .utils import filter_cookies_to_query_string

logger = logging.getLogger(__name__)


def check_login_status(
    site_name: str,
    default_check_url: str,
    base_headers: dict[str, str],
    parse_response: Callable[[httpx.Response], LoginStatusResult],
    *,
    default_timeout: float = 20,
    fetch_page: Callable[[str, dict[str, str], float], httpx.Response] | None = None,
    get_cookies: Callable[[str], str | None] | None = None,
) -> LoginStatusResult:
    """Shared login status check for all sites.

    Steps 1-4: Get config, get cookies, build headers, make request.
    Step 5: Delegated to parse_response callback.

    For sites with custom fetch logic (e.g. Pornhub age bypass),
    pass a fetch_page callable.

    For sites with custom cookie lookup (e.g. JavDB via html_client),
    pass a get_cookies callable returning header dict or None.
    """
    login_config = get_login_config(site_name)
    check_url = login_config.get("check_url") or default_check_url

    if get_cookies:
        cookie_header = get_cookies(check_url)
        if not cookie_header:
            return LoginStatusResult(
                site_name=site_name,
                logged_in=False,
                message=f"cookies.txt 中未找到 {site_name.title()} 条目",
            )
        headers = get_login_headers(site_name, base_headers)
        headers["Cookie"] = cookie_header
    else:
        cookies = filter_cookies_to_query_string(check_url)
        if not cookies:
            return LoginStatusResult(
                site_name=site_name,
                logged_in=False,
                message=f"cookies.txt 中未找到 {site_name.title()} 条目",
            )
        headers = get_login_headers(site_name, base_headers)
        headers["Cookie"] = cookies

    timeout = float(login_config.get("timeout", default_timeout))

    fetcher = fetch_page or _default_fetch_page
    try:
        resp = fetcher(check_url, headers, timeout)
    except Exception as exc:
        logger.warning("%s login check failed: %s", site_name, exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    return parse_response(resp)


def _default_fetch_page(url: str, headers: dict[str, str], timeout: float) -> httpx.Response:
    return request_without_limit("GET", url, headers=headers, timeout=timeout)
