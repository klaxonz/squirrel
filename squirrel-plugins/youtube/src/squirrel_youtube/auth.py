from __future__ import annotations

import logging
import re
from html import unescape

from crawl import (
    LoginStatusResult,
    filter_cookies_to_query_string,
    request_without_limit,
    get_login_config,
    get_login_headers,
)

logger = logging.getLogger(__name__)

_CHANNELS_URL = "https://www.youtube.com/feed/channels"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_LOGGED_FLAG = re.compile(r'"LOGGED_IN":\s*(true|false)', re.IGNORECASE)
_ACCOUNT_LABEL = re.compile(r'"ACCOUNT_LABEL":"([^"]+)"')


def check_youtube_login_status() -> LoginStatusResult:
    site_name = "youtube"
    login_config = get_login_config(site_name)
    check_url = login_config.get("check_url") or _CHANNELS_URL

    cookies = filter_cookies_to_query_string(check_url)

    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="cookies.txt 中未找到 YouTube 条目",
        )

    headers = get_login_headers(site_name, _HEADERS)
    headers["Cookie"] = cookies
    timeout = float(login_config.get("timeout", 20))

    try:
        resp = request_without_limit("GET", check_url, headers=headers, timeout=timeout)
        body = resp.text or ""
    except Exception as exc:
        logger.warning("youtube login check failed: %s", exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    match = _LOGGED_FLAG.search(body)
    if match and match.group(1).lower() == "true":
        label_match = _ACCOUNT_LABEL.search(body)
        username = unescape(label_match.group(1)) if label_match else None
        return LoginStatusResult(
            site_name=site_name,
            logged_in=True,
            username=username,
            message="已登录",
        )

    redirected_url = resp.url or ""
    if "consent.youtube.com" in redirected_url:
        msg = "需要先通过 Google Consent 页面"
    elif "service_login" in redirected_url:
        msg = "已被重定向到登录页"
    else:
        msg = "检测到 LOGGED_IN=false"

    return LoginStatusResult(
        site_name=site_name,
        logged_in=False,
        message=msg,
        extra={"redirect_url": redirected_url},
    )
