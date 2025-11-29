from __future__ import annotations

import logging
import re

from crawl import (
    LoginStatusResult,
    filter_cookies_to_query_string,
    register_login_checker,
    request_without_limit,
)

logger = logging.getLogger(__name__)

_CHECK_URL = "https://www.pornhub.com/users/edit"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_USERNAME_PATTERN = re.compile(r'id="nickname"[^>]*value="([^"]+)"')


@register_login_checker("pornhub")
def check_pornhub_login_status() -> LoginStatusResult:
    site_name = "pornhub"
    cookies = filter_cookies_to_query_string(_CHECK_URL)

    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="cookies.txt 中未找到 Pornhub 条目",
        )

    headers = dict(_HEADERS)
    headers["Cookie"] = cookies

    try:
        resp = request_without_limit(
            "GET",
            _CHECK_URL,
            headers=headers,
            timeout=20,
            allow_redirects=False,
        )
        body = resp.text or ""
    except Exception as exc:
        logger.warning("pornhub login check failed: %s", exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    location = resp.headers.get("Location", "")
    redirected_to_login = any(
        token in location for token in ("/login", "/users/login")
    )

    if resp.status_code in (301, 302, 303, 307, 308) and redirected_to_login:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="被重定向到登录页",
            extra={"redirect_url": location},
        )

    if resp.status_code in (401, 403):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"权限被拒绝 (status={resp.status_code})",
        )

    if "/login" in (resp.url or "") or "/login" in body:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="响应内容为登录页面",
        )

    username = None
    match = _USERNAME_PATTERN.search(body)
    if match:
        username = match.group(1).strip()

    return LoginStatusResult(
        site_name=site_name,
        logged_in=True,
        username=username,
        message="已登录",
    )
