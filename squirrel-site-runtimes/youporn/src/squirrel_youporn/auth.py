from __future__ import annotations

import logging
import re

from crawl import LoginStatusResult, check_login_status

logger = logging.getLogger(__name__)

_CHECK_URL = 'https://www.youporn.com/'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
_USERNAME_PATTERN = re.compile(r"liu_username\s*=\s*'([^']*)'", re.IGNORECASE)
_LOGGED_IN_PATTERN = re.compile(r'isLoggedInUser\s*=\s*true', re.IGNORECASE)
_LOGGED_OUT_PATTERN = re.compile(r'isLoggedInUser\s*=\s*false', re.IGNORECASE)
_PROFILE_LINK_PATTERN = re.compile(r'href="/users/([^"/?#]+)"', re.IGNORECASE)


def check_youporn_login_status() -> LoginStatusResult:
    return check_login_status(
        site_name='youporn',
        default_check_url=_CHECK_URL,
        base_headers=_HEADERS,
        parse_response=_parse_response,
    )


def _parse_response(resp) -> LoginStatusResult:
    site_name = 'youporn'
    body = resp.text or ''

    if resp.status_code in (401, 403):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f'被拒绝访问 (status={resp.status_code})',
        )

    final_url = str(resp.url or '')
    if '/login' in final_url:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message='被重定向到登录页',
            extra={'redirect_url': final_url},
        )

    username = _extract_username(body)
    if username and _LOGGED_IN_PATTERN.search(body):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=True,
            username=username,
            message='已登录',
        )

    if _LOGGED_OUT_PATTERN.search(body):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message='未登录',
        )

    return LoginStatusResult(
        site_name=site_name,
        logged_in=bool(username),
        username=username,
        message='已登录' if username else '未检测到登录标记',
    )


def _extract_username(body: str) -> str | None:
    match = _USERNAME_PATTERN.search(body)
    if match:
        username = match.group(1).strip()
        if username:
            return username

    profile_match = _PROFILE_LINK_PATTERN.search(body)
    if profile_match:
        username = profile_match.group(1).strip()
        if username:
            return username

    return None
