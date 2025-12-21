"""HTTP utilities with shared rate-limited session for plugins."""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SECONDS = 20


def _extract_second_level_domain(domain_or_url: str) -> str:
    if not domain_or_url:
        return domain_or_url

    if "://" in domain_or_url:
        parsed = urlparse(domain_or_url)
        domain = parsed.hostname or domain_or_url
    else:
        domain = domain_or_url

    parts = domain.lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


@dataclass(frozen=True)
class RateLimit:
    min_interval: float
    max_interval: float
    domain: str


DEFAULT_DOMAIN_LIMITS: Dict[str, RateLimit] = {
    "bilibili.com": RateLimit(3, 5, "bilibili.com"),
    "youtube.com": RateLimit(2, 5, "youtube.com"),
    "pornhub.com": RateLimit(3, 8, "pornhub.com"),
    "javdb.com": RateLimit(5, 8, "javdb.com"),
    "googlevideo.com": RateLimit(1, 2, "googlevideo.com"),
}


class RateLimiter:
    def __init__(
        self,
        default_limit: Optional[RateLimit] = None,
        domain_limits: Optional[Dict[str, RateLimit]] = None,
    ) -> None:
        self._default_limit = default_limit or RateLimit(3, 5, "*")
        provided_limits = domain_limits or {}
        self._rate_limits: Dict[str, RateLimit] = dict(provided_limits)
        self._last_request_time: Dict[str, float] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def set_default(self, min_interval: float, max_interval: float) -> None:
        self._default_limit = RateLimit(min_interval, max_interval, "*")

    def add_rate_limit(self, domain: str, min_interval: float, max_interval: float) -> None:
        sld = _extract_second_level_domain(domain)
        self._rate_limits[sld] = RateLimit(min_interval, max_interval, sld)

    def get_rate_limit(self, domain: Optional[str]) -> RateLimit:
        if not domain:
            return self._default_limit
        sld = _extract_second_level_domain(domain)
        return self._rate_limits.get(sld, self._default_limit)

    def _get_lock(self, bucket: str) -> threading.Lock:
        lock = self._locks.get(bucket)
        if lock is None:
            with self._locks_guard:
                lock = self._locks.get(bucket)
                if lock is None:
                    lock = threading.Lock()
                    self._locks[bucket] = lock
        return lock

    def wait(self, domain: Optional[str] = None) -> None:
        bucket = _extract_second_level_domain(domain) if domain else "*"
        if not bucket:
            bucket = "*"

        lock = self._get_lock(bucket)
        rate_limit = self.get_rate_limit(bucket)

        with lock:
            last_time = self._last_request_time.get(bucket, 0.0)
            now = time.time()
            elapsed = now - last_time
            interval = random.uniform(rate_limit.min_interval, rate_limit.max_interval)

            if elapsed < interval:
                sleep_time = interval - elapsed
                logger.debug("Rate limiter sleeping %.3fs for bucket %s", sleep_time, bucket)
                time.sleep(sleep_time)

            self._last_request_time[bucket] = time.time()


class RateLimitedSession(requests.Session):
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        retries: int = 3,
        backoff_factor: float = 0.3,
    ) -> None:
        super().__init__()
        self._rate_limiter = rate_limiter or RateLimiter()

        self.headers["Accept-Encoding"] = "gzip, deflate"

        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )

        adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def request(self, method: str, url: str, **kwargs):  # type: ignore[override]
        domain = None
        if url:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "") if parsed.netloc else url
        self._rate_limiter.wait(domain)

        kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)
        return super().request(method, url, **kwargs)


_default_rate_limiter = RateLimiter(domain_limits=DEFAULT_DOMAIN_LIMITS)
_shared_session: Optional[RateLimitedSession] = None
_session_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    return _default_rate_limiter


def configure_rate_limit(domain: str, min_interval: float, max_interval: float) -> None:
    _default_rate_limiter.add_rate_limit(domain, min_interval, max_interval)


def set_default_rate_limit(min_interval: float, max_interval: float) -> None:
    _default_rate_limiter.set_default(min_interval, max_interval)


def get_http_session() -> RateLimitedSession:
    global _shared_session
    if _shared_session is None:
        with _session_lock:
            if _shared_session is None:
                _shared_session = RateLimitedSession(rate_limiter=_default_rate_limiter)
    return _shared_session


def request(method: str, url: str, use_cloudflare_bypass: bool = False, **kwargs):
    """
    发送HTTP请求（支持rate limiting和cloudflare bypass）

    Args:
        method: HTTP方法
        url: 目标URL
        use_cloudflare_bypass: 是否使用cloudflare bypass
        **kwargs: 其他请求参数

    Returns:
        requests.Response对象
    """
    if use_cloudflare_bypass:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "") if parsed.netloc else url

        _default_rate_limiter.wait(domain)

        cookies = kwargs.get('cookies')
        if isinstance(cookies, dict):
            cookies = '; '.join([f"{k}={v}" for k, v in cookies.items()])

        result = fetch_with_cloudflare_bypass(
            url=url,
            cookies=cookies,
            follow_redirects=kwargs.get('allow_redirects', True),
            max_redirects=kwargs.get('max_redirects', 5)
        )

        response = requests.Response()
        if result.success:
            response.status_code = 200
            response._content = result.html.encode('utf-8') if result.html else b''
            response.url = result.final_url
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        else:
            response.status_code = 500
            response._content = (result.error or 'Unknown error').encode('utf-8')
            response.url = result.final_url
        return response
    else:
        session = get_http_session()
        return session.request(method, url, **kwargs)


def request_without_limit(method: str, url: str, use_cloudflare_bypass: bool = False, **kwargs):
    """
    发送HTTP请求（不限流，支持cloudflare bypass）

    Args:
        method: HTTP方法
        url: 目标URL
        use_cloudflare_bypass: 是否使用cloudflare bypass
        **kwargs: 其他请求参数

    Returns:
        requests.Response对象
    """
    if use_cloudflare_bypass:
        cookies = kwargs.get('cookies')
        if isinstance(cookies, dict):
            cookies = '; '.join([f"{k}={v}" for k, v in cookies.items()])

        result = fetch_with_cloudflare_bypass(
            url=url,
            cookies=cookies,
            follow_redirects=kwargs.get('allow_redirects', True),
            max_redirects=kwargs.get('max_redirects', 5)
        )

        response = requests.Response()
        if result.success:
            response.status_code = 200
            response._content = result.html.encode('utf-8') if result.html else b''
            response.url = result.final_url
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        else:
            response.status_code = 500
            response._content = (result.error or 'Unknown error').encode('utf-8')
            response.url = result.final_url
        return response
    else:
        session = requests.Session()

        # Keep encoding to gzip/deflate only to avoid Brotli-related decode errors
        session.headers["Accept-Encoding"] = "gzip, deflate"

        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)
        return session.request(method, url, **kwargs)


def get(url: str, use_cloudflare_bypass: bool = False, **kwargs):
    """
    发送GET请求（支持rate limiting和cloudflare bypass）

    Args:
        url: 目标URL
        use_cloudflare_bypass: 是否使用cloudflare bypass
        **kwargs: 其他请求参数

    Returns:
        requests.Response对象
    """
    return request('GET', url, use_cloudflare_bypass=use_cloudflare_bypass, **kwargs)


def post(url: str, use_cloudflare_bypass: bool = False, **kwargs):
    """
    发送POST请求（支持rate limiting和cloudflare bypass）

    Args:
        url: 目标URL
        use_cloudflare_bypass: 是否使用cloudflare bypass
        **kwargs: 其他请求参数

    Returns:
        requests.Response对象
    """
    return request('POST', url, use_cloudflare_bypass=use_cloudflare_bypass, **kwargs)


_cloudflare_bypass_client: Optional[object] = None


def configure_cloudflare_bypass_client(client: object) -> None:
    """配置 Cloudflare bypass 客户端（由后端注入）"""
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client
    logger.info("Cloudflare bypass client configured")


def fetch_with_cloudflare_bypass(
    url: str,
    cookies: Optional[str] = None,
    follow_redirects: bool = True,
    max_redirects: int = 5
):
    """
    使用 Cloudflare bypass 服务获取页面内容

    Args:
        url: 目标 URL
        cookies: Cookie 字符串
        follow_redirects: 是否跟随重定向
        max_redirects: 最大重定向次数

    Returns:
        CloudflareBypassResult 对象，包含：
        - success: bool - 是否成功
        - final_url: str - 最终 URL
        - html: Optional[str] - HTML 内容
        - error: Optional[str] - 错误信息
        - redirect_count: int - 重定向次数
        - elapsed: float - 耗时（秒）

    Raises:
        RuntimeError: 如果客户端未配置
    """
    if _cloudflare_bypass_client is None:
        raise RuntimeError(
            "Cloudflare bypass client not configured. "
            "Backend should call configure_cloudflare_bypass_client() during startup."
        )

    return _cloudflare_bypass_client.fetch(  # type: ignore
        url=url,
        cookies=cookies,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects
    )


