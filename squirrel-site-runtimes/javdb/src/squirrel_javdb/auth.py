from __future__ import annotations

import logging
import re

import httpx
from crawl import LoginStatusResult, check_login_status

from .html_client import DEFAULT_JAVDB_TIMEOUT_SECONDS, build_javdb_headers, fetch_javdb_html

logger = logging.getLogger(__name__)

_CHECK_URL = "https://javdb.com/users/collection_actors"
_LOGIN_REDIRECT = re.compile(r"/(users/)?(sign_in|login)")


def check_javdb_login_status() -> LoginStatusResult:
    def _get_cookies(_check_url: str) -> str | None:
        return build_javdb_headers(_check_url, login=True).get("Cookie")

    def _fetch(url: str, headers: dict[str, str], _timeout: float) -> httpx.Response:
        return fetch_javdb_html(
            url, login=True, timeout=_timeout, allow_redirects=False, use_rate_limit=False,
        )

    return check_login_status(
        site_name="javdb",
        default_check_url=_CHECK_URL,
        base_headers={},
        parse_response=_parse_response,
        default_timeout=DEFAULT_JAVDB_TIMEOUT_SECONDS,
        fetch_page=_fetch,
        get_cookies=_get_cookies,
    )


def _parse_response(resp) -> LoginStatusResult:
    site_name = "javdb"
    body = resp.text or ""

    if resp.status_code == 401:
        return LoginStatusResult(
            site_name=site_name,
            logged_in=False,
            message=f"认证失败 (status={resp.status_code})",
        )

    if resp.status_code in (403, 404, 429):
        reason = "页面不存在(404)" if resp.status_code == 404 else f"被拒绝访问 (status={resp.status_code})"
        return _transient_login_failure(site_name, reason)

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

    if _looks_like_javdb_error_page(body):
        return _transient_login_failure(site_name, "返回内容显示为站点错误页")

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


def _looks_like_javdb_error_page(body: str) -> bool:
    normalized_body = str(body or "").lower()
    if not normalized_body:
        return False
    if "<title>just a moment" in normalized_body:
        return True
    if "cf-error-details" in normalized_body and (
        "bad gateway" in normalized_body or "error code 502" in normalized_body
    ):
        return True
    return False


def _transient_login_failure(site_name: str, reason: str) -> LoginStatusResult:
    return LoginStatusResult(
        site_name=site_name,
        logged_in=False,
        message=f"检测失败: {reason}",
        extra={"transient_failure": True},
    )
