from __future__ import annotations

import logging
import re
from html import unescape

from crawl import LoginStatusResult, check_login_status

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
    return check_login_status(
        site_name="youtube",
        default_check_url=_CHANNELS_URL,
        base_headers=_HEADERS,
        parse_response=_parse_response,
    )


def _parse_response(resp) -> LoginStatusResult:
    site_name = "youtube"
    body = resp.text or ""

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

    redirected_url = str(resp.url or "")
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
