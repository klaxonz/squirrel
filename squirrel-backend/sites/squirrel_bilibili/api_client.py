from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

from sites.crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    filter_cookies_to_query_string,
    get_http_headers,
    request,
    request_without_limit,
)

SITE_SLUG = "bilibili"

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json",
}


def _cookie_source_url(target_url: str) -> str:
    parsed = urlparse(target_url)
    host = (parsed.hostname or "").lower()
    if host.endswith("b23.tv"):
        return "https://www.bilibili.com/"
    return target_url


def build_cookies(target_url: str) -> str:
    return filter_cookies_to_query_string(_cookie_source_url(target_url))


def _build_headers(cookies: str) -> dict[str, str]:
    headers = get_http_headers(SITE_SLUG, _DEFAULT_HEADERS)
    if cookies:
        headers["Cookie"] = cookies
    return headers


def _send_request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    cookies: str = "",
    timeout: float = 20,
    throttled: bool = True,
    allow_redirects: bool = True,
):
    kwargs: dict[str, Any] = {
        "headers": _build_headers(cookies),
        "timeout": timeout,
        "allow_redirects": allow_redirects,
    }
    if params:
        kwargs["params"] = params
    if throttled:
        return request(method, url, **kwargs)
    return request_without_limit(method, url, **kwargs)


def _raise_api_code_error(code: int, message: str, url: str) -> None:
    """Translate a non-zero bilibili API code into a typed site error.

    Known codes: -404 not found, -101/-403 login/access denied, -412 request
    intercepted (risk control, retryable), -400 bad request. Unknown codes
    degrade to ParseError.
    """
    context = {"url": url, "code": code, "original_error": message}
    if code == -404:
        raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
    if code in (-101, -403):
        raise AuthError(f"需要登录或访问权限: {url}", context=context)
    if code == -412:
        raise RateLimitError(f"请求被拦截,请稍后重试: {url}", context=context)
    raise ParseError(f"Bilibili API 返回错误: {message} (code={code})", context=context)


def _translate_http_error(exc: Exception, url: str) -> None:
    """Translate an HTTP-level failure into a typed site error."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    context = {"url": url, "original_error": str(exc)}
    if status == 404:
        raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
    if status in (401, 403):
        raise AuthError(f"需要登录或访问权限: {url}", context=context)
    if status == 429:
        raise RateLimitError(f"请求频率过高: {url}", context=context)
    if status is not None and status >= 500:
        raise NetworkError(f"Bilibili 服务异常 (HTTP {status}): {url}", context=context)
    raise NetworkError(f"Bilibili 请求失败: {url}", context=context)


def _get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    cookies: str = "",
    throttled: bool = True,
    timeout: float = 20,
) -> dict:
    try:
        resp = _send_request(
            "GET",
            url,
            params=params,
            cookies=cookies,
            timeout=timeout,
            throttled=throttled,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        if isinstance(exc, (AuthError, NetworkError, NotFoundError, ParseError, RateLimitError)):
            raise
        _translate_http_error(exc, url)
        raise
    payload = resp.json()
    if isinstance(payload, dict) and payload.get("code") not in (None, 0):
        code = payload.get("code")
        message = payload.get("message") or payload.get("msg") or str(code)
        _raise_api_code_error(int(code), str(message), url)
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data") or {}
    return payload if isinstance(payload, dict) else {}


def _resolve_redirect_url(
    url: str,
    *,
    cookies: str = "",
    throttled: bool = True,
    max_hops: int = 5,
) -> str:
    current = url
    for _ in range(max_hops):
        resp = _send_request(
            "GET",
            current,
            cookies=cookies,
            timeout=15,
            throttled=throttled,
            allow_redirects=False,
        )
        if resp.is_redirect or resp.is_permanent_redirect or (300 <= resp.status_code < 400):
            location = resp.headers.get("Location") or resp.headers.get("location")
            if not location:
                break
            current = urljoin(current, location)
            continue
        break
    return current
