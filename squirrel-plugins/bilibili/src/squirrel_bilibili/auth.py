from __future__ import annotations

import logging

from crawl import (
    LoginStatusResult,
    filter_cookies_to_query_string,
    request_without_limit,
    get_login_config,
    get_login_headers,
)

logger = logging.getLogger(__name__)

_CHECK_URL = "https://api.bilibili.com/x/web-interface/nav"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


def check_bilibili_login_status() -> LoginStatusResult:
    site_name = "bilibili"
    login_config = get_login_config(site_name)
    check_url = login_config.get("check_url") or _CHECK_URL

    cookies = filter_cookies_to_query_string(check_url)

    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="cookies.txt 中未找到 Bilibili 条目",
        )

    headers = get_login_headers(site_name, _HEADERS)
    headers["Cookie"] = cookies
    timeout = float(login_config.get("timeout", 15))

    try:
        resp = request_without_limit("GET", check_url, headers=headers, timeout=timeout)
        payload = resp.json()
    except Exception as exc:
        logger.warning("bilibili login check failed: %s", exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    if payload.get("code") == 0:
        data = payload.get("data") or {}
        if data.get("isLogin"):
            level_info = data.get("level_info") or {}
            extra = {
                "level": level_info.get("current_level"),
                "vipType": data.get("vipType"),
            }
            return LoginStatusResult(
                site_name=site_name,
                logged_in=True,
                username=data.get("uname"),
                user_id=str(data.get("mid") or ""),
                message="已登录",
                extra=extra,
            )

    message = payload.get("message") or payload.get("data", {}).get("message")
    return LoginStatusResult(
        site_name=site_name,
        logged_in=False,
        message=message or "未登录或 Cookie 已过期",
    )
