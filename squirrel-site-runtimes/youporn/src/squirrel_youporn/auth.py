from __future__ import annotations

import logging
import re

from crawl import (
    LoginStatusResult,
    filter_cookies_to_query_string,
    get_login_config,
    get_login_headers,
    request_without_limit,
)

logger = logging.getLogger(__name__)

CHECK_URL = 'https://www.youporn.com/'
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
USERNAME_PATTERN = re.compile(r"liu_username\s*=\s*'([^']*)'", re.IGNORECASE)
LOGGED_IN_PATTERN = re.compile(r'isLoggedInUser\s*=\s*true', re.IGNORECASE)
LOGGED_OUT_PATTERN = re.compile(r'isLoggedInUser\s*=\s*false', re.IGNORECASE)
PROFILE_LINK_PATTERN = re.compile(r'href="/users/([^"/?#]+)"', re.IGNORECASE)


def check_youporn_login_status() -> LoginStatusResult:
    site_name = 'youporn'
    login_config = get_login_config(site_name)
    check_url = login_config.get('check_url') or CHECK_URL

    cookies = filter_cookies_to_query_string(check_url)
    if not cookies:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message='cookies.txt 中未找到 YouPorn 条目',
        )

    headers = get_login_headers(site_name, DEFAULT_HEADERS)
    headers['Cookie'] = cookies

    timeout = float(login_config.get('timeout', 20))
    try:
        response = request_without_limit(
            'GET',
            check_url,
            headers=headers,
            timeout=timeout,
        )
    except Exception as exc:  # HTTP/API boundary — network or transport errors
        logger.warning('youporn login check failed: %s', exc, exc_info=True)
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f'请求失败: {exc}',
        )

    body = response.text or ''
    if response.status_code in (401, 403):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f'被拒绝访问 (status={response.status_code})',
        )

    final_url = response.url or check_url
    if '/login' in final_url:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message='被重定向到登录页',
            extra={'redirect_url': final_url},
        )

    username = _extract_username(body)
    if username and LOGGED_IN_PATTERN.search(body):
        return LoginStatusResult(
            site_name=site_name,
            logged_in=True,
            username=username,
            message='已登录',
        )

    if LOGGED_OUT_PATTERN.search(body):
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
    match = USERNAME_PATTERN.search(body)
    if match:
        username = match.group(1).strip()
        if username:
            return username

    profile_match = PROFILE_LINK_PATTERN.search(body)
    if profile_match:
        username = profile_match.group(1).strip()
        if username:
            return username

    return None
