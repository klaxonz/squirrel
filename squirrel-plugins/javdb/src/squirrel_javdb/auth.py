from __future__ import annotations

import logging
import re

from crawl import (
    LoginStatusResult,
    filter_cookies_to_query_string,
    register_login_checker,
    request_without_limit,
    get_login_config,
    get_login_headers,
)

logger = logging.getLogger(__name__)

_CHECK_URL = "https://javdb.com/users/collection_actors"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
_LOGIN_REDIRECT = re.compile(r"/(users/)?(sign_in|login)")


@register_login_checker("javdb")
def check_javdb_login_status() -> LoginStatusResult:
    site_name = "javdb"
    login_config = get_login_config(site_name)
    check_url = login_config.get("check_url") or _CHECK_URL

    cookies = filter_cookies_to_query_string(check_url)

    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="cookies.txt 中未找到 JavDB 条目",
        )

    headers = get_login_headers(site_name, _HEADERS)
    headers["Cookie"] = cookies
    timeout = float(login_config.get("timeout", 15))

    try:
        resp = request_without_limit(
            "GET",
            check_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )
        body = resp.text or ""
    except Exception as exc:
        logger.warning("javdb login check failed: %s", exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    if resp.status_code == 404:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="页面不存在(404)",
        )

    location = resp.headers.get("Location", "")
    if resp.status_code in (301, 302, 303, 307, 308) and _LOGIN_REDIRECT.search(location):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="被重定向到登录页",
            extra={"redirect_url": location},
        )

    if _LOGIN_REDIRECT.search(body):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="返回内容显示为登录页",
        )

    username = None
    match = re.search(r'data-username="([^"]+)"', body)
    if match:
        username = match.group(1).strip()

    return LoginStatusResult(
        site_name=site_name,
        logged_in=True,
        username=username,
        message="已登录",
    )
