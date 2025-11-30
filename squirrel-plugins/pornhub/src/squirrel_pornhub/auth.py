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

_CHECK_URL = "https://www.pornhub.com/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_LOGGED_IN_PATTERN = re.compile(r'"loggedIn(?:Context)?":\s*true', re.IGNORECASE)
_LOGGED_OUT_PATTERN = re.compile(r'"loggedIn(?:Context)?":\s*false', re.IGNORECASE)
_AGE_GATE_PATTERN = re.compile(r"agecheck|ageverification|ageDisclaimer", re.IGNORECASE)
_USERNAME_PATTERN = re.compile(r'"username"\s*:\s*"([^"]+)"', re.IGNORECASE)
_DATA_USERNAME_PATTERN = re.compile(r'data-username="([^"]+)"')
_PROFILE_BLOCK_PATTERN = re.compile(
    r'<div[^>]+class="profile"[\s\S]*?class="js_userName"[^>]*>([^<]+)<',
    re.IGNORECASE,
)
_PROFILE_STATUS_PATTERN = re.compile(
    r'class="userUserStatus[^"]*">\s*See Your Profile',
    re.IGNORECASE,
)


@register_login_checker("pornhub")
def check_pornhub_login_status() -> LoginStatusResult:
    site_name = "pornhub"
    login_config = get_login_config(site_name)
    check_url = login_config.get("check_url") or _CHECK_URL

    cookies = filter_cookies_to_query_string(check_url)

    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="cookies.txt 中未找到 Pornhub 条目",
        )

    headers = get_login_headers(site_name, _HEADERS)
    headers["Cookie"] = cookies

    resp = _fetch_with_age_bypass(headers, check_url, login_config)
    if isinstance(resp, LoginStatusResult):
        return resp

    body = resp.text or ""

    if resp.status_code in (401, 403):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"被拒绝访问 (status={resp.status_code})",
        )

    final_url = resp.url or check_url
    if any(token in final_url for token in ("/login", "/users/login")):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message="被重定向到登录页",
            extra={"redirect_url": final_url},
        )

    profile_match = _PROFILE_BLOCK_PATTERN.search(body)
    if profile_match or _PROFILE_STATUS_PATTERN.search(body):
        username = profile_match.group(1).strip() if profile_match else None
        return LoginStatusResult(
            site_name=site_name,
            logged_in=True,
            username=username,
            message="已登录",
        )

    if _LOGGED_IN_PATTERN.search(body):
        username = None
        match = _USERNAME_PATTERN.search(body) or _DATA_USERNAME_PATTERN.search(body)
        if match:
            username = match.group(1).strip()
        return LoginStatusResult(
            site_name=site_name,
            logged_in=True,
            username=username,
            message="已登录",
        )

    message = "未检测到登录标记"
    if _LOGGED_OUT_PATTERN.search(body):
        message = "未登录"

    return LoginStatusResult(
        site_name=site_name,
        logged_in=False,
        message=message,
    )


def _fetch_with_age_bypass(headers: dict, check_url: str, login_config: dict):
    timeout = float(login_config.get("timeout", 20))
    try:
        resp = request_without_limit(
            "GET",
            check_url,
            headers=headers,
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning("pornhub login check failed: %s", exc, exc_info=True)
        return LoginStatusResult(
            site_name="pornhub",
            logged_in=False,
            message=f"请求失败: {exc}",
        )

    body = resp.text or ""
    if _is_age_gate(resp.url or "", body):
        extra_headers = dict(headers)
        cookie = headers.get("Cookie", "")
        age_cookies = "age_verified=1; accessAgeDisclaimerPH=1"
        extra_headers["Cookie"] = f"{cookie}; {age_cookies}" if cookie else age_cookies
        try:
            resp = request_without_limit(
                "GET",
                check_url,
                headers=extra_headers,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("pornhub age bypass failed: %s", exc, exc_info=True)
            return resp

    return resp


def _is_age_gate(url: str, body: str) -> bool:
    return bool(_AGE_GATE_PATTERN.search(url) or _AGE_GATE_PATTERN.search(body))
