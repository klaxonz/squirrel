"""HTTP utilities with shared rate-limited session for plugins."""

from __future__ import annotations

from contextlib import nullcontext
import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Set, TypeVar
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

T = TypeVar('T')
S = TypeVar('S')

DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_PROXY_ROTATE_RETRIES = 3


def _extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '') if parsed.netloc else url
    return domain or None


def _safe_report_proxy_result(
    proxy_provider: Optional[object],
    proxy_info: Optional[object],
    domain: Optional[str],
    success: bool,
) -> None:
    if not proxy_provider or not proxy_info or not domain:
        return
    try:
        proxy_provider.report_result(proxy_info, domain, success)  # type: ignore[attr-defined]
    except Exception as e:
        logger.warning('Failed to report proxy result: %s', e)


def _should_rotate_proxy(exception: Exception) -> bool:
    return isinstance(
        exception,
        (
            requests.exceptions.ProxyError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.RetryError,
        ),
    )


def _request_with_proxy_rotation(
    do_request: Callable[[Dict[str, Any]], requests.Response],
    *,
    proxy_provider: Optional[object],
    domain: Optional[str],
    base_kwargs: Dict[str, Any],
) -> requests.Response:
    explicit_proxies = 'proxies' in base_kwargs
    rotate_retries_raw = base_kwargs.pop('proxy_rotate_retries', None)
    try:
        proxy_rotate_retries = int(rotate_retries_raw) if rotate_retries_raw is not None else DEFAULT_PROXY_ROTATE_RETRIES
    except Exception:
        proxy_rotate_retries = DEFAULT_PROXY_ROTATE_RETRIES

    if explicit_proxies or not proxy_provider or not domain or proxy_rotate_retries <= 0:
        return do_request(base_kwargs)

    last_exception: Optional[Exception] = None
    for attempt in range(proxy_rotate_retries + 1):
        attempt_kwargs = dict(base_kwargs)
        proxy_info = None

        try:
            proxy_info = proxy_provider.get_proxy(domain)  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning('Failed to get proxy for domain=%s: %s', domain, e)
            proxy_info = None

        if proxy_info:
            attempt_kwargs['proxies'] = proxy_info.to_dict()  # type: ignore[attr-defined]
        else:
            attempt_kwargs.pop('proxies', None)

        try:
            response = do_request(attempt_kwargs)
            _safe_report_proxy_result(proxy_provider, proxy_info, domain, True)
            return response
        except Exception as e:
            last_exception = e
            _safe_report_proxy_result(proxy_provider, proxy_info, domain, False)
            if attempt >= proxy_rotate_retries or not proxy_info or not _should_rotate_proxy(e):
                raise

    if last_exception:
        raise last_exception
    raise RuntimeError('Proxy rotation retries exhausted')


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
        self._disabled_domains: Set[str] = set()
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def set_default(self, min_interval: float, max_interval: float) -> None:
        self._default_limit = RateLimit(min_interval, max_interval, "*")

    def add_rate_limit(self, domain: str, min_interval: float, max_interval: float) -> None:
        sld = _extract_second_level_domain(domain)
        self._disabled_domains.discard(sld)
        self._rate_limits[sld] = RateLimit(min_interval, max_interval, sld)

    def set_domain_enabled(self, domain: str, enabled: bool) -> None:
        sld = _extract_second_level_domain(domain)
        if not sld:
            return
        if enabled:
            self._disabled_domains.discard(sld)
            return
        self._disabled_domains.add(sld)

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
        if bucket in self._disabled_domains:
            return

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
        domain = _extract_domain(url)
        self._rate_limiter.wait(domain)

        kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)

        from .proxy_provider import get_proxy_provider
        proxy_provider = get_proxy_provider()

        return _request_with_proxy_rotation(
            lambda attempt_kwargs: super().request(method, url, **attempt_kwargs),
            proxy_provider=proxy_provider,
            domain=domain,
            base_kwargs=kwargs,
        )


_default_rate_limiter = RateLimiter(domain_limits=DEFAULT_DOMAIN_LIMITS)
_shared_session: Optional[RateLimitedSession] = None
_session_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    return _default_rate_limiter


def configure_rate_limit(domain: str, min_interval: float, max_interval: float) -> None:
    _default_rate_limiter.add_rate_limit(domain, min_interval, max_interval)


def configure_rate_limit_enabled(domain: str, enabled: bool) -> None:
    _default_rate_limiter.set_domain_enabled(domain, enabled)


def set_default_rate_limit(min_interval: float, max_interval: float) -> None:
    _default_rate_limiter.set_default(min_interval, max_interval)


def get_http_session() -> RateLimitedSession:
    global _shared_session
    if _shared_session is None:
        with _session_lock:
            if _shared_session is None:
                _shared_session = RateLimitedSession(rate_limiter=_default_rate_limiter)
    return _shared_session


def execute_with_rate_limit_and_proxy_rotation(
    execute_func: Callable[[], T],
    *,
    domain: str,
    throttled: bool = True,
    use_proxy_rotation: bool = True,
    configure_proxy: Optional[Callable[[Optional[str]], None]] = None,
    capture_state: Optional[Callable[[], S]] = None,
    restore_state: Optional[Callable[[S], None]] = None,
    lock: Optional[object] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None,
    max_retries: int = DEFAULT_PROXY_ROTATE_RETRIES,
) -> T:
    if throttled:
        _default_rate_limiter.wait(domain)

    guard = lock if lock is not None else nullcontext()
    with guard:
        state = capture_state() if capture_state else None
        try:
            if use_proxy_rotation and configure_proxy:
                from .proxy_provider import execute_with_proxy_rotation

                return execute_with_proxy_rotation(
                    domain=domain,
                    execute_func=execute_func,
                    configure_callback=configure_proxy,
                    restore_callback=None,
                    should_retry=should_retry,
                    max_retries=max_retries,
                )

            if configure_proxy:
                configure_proxy(None)
            return execute_func()
        finally:
            if restore_state and capture_state:
                restore_state(state)  # type: ignore[arg-type]


def request(method: str, url: str, **kwargs):
    """
    发送HTTP请求（支持rate limiting和cloudflare bypass）

    Args:
        method: HTTP方法
        url: 目标URL
        **kwargs: 其他请求参数，包括可选的 bypass_mode 参数

    Kwargs:
        bypass_mode: Cloudflare bypass 方式，可选值为 'html'、'mirror' 或 None

    Returns:
        requests.Response对象
    """
    use_cloudflare_bypass = kwargs.pop('bypass_mode', None)

    if use_cloudflare_bypass:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "") if parsed.netloc else url

        _default_rate_limiter.wait(domain)

        headers = kwargs.get('headers')

        if use_cloudflare_bypass == "html":
            return _cloudflare_bypass_client.html(url=url, headers=headers)  # type: ignore
        elif use_cloudflare_bypass == "mirror":
            return _cloudflare_bypass_client.mirror(url=url, headers=headers)  # type: ignore
        else:
            raise ValueError(f"无效的 Cloudflare bypass 类型: {use_cloudflare_bypass}，应为 'html' 或 'mirror'")
    else:
        session = get_http_session()
        return session.request(method, url, **kwargs)


def request_without_limit(method: str, url: str, **kwargs):
    """
    发送HTTP请求（不限流，支持cloudflare bypass）

    Args:
        method: HTTP方法
        url: 目标URL
        **kwargs: 其他请求参数，包括可选的 bypass_mode 参数

    Kwargs:
        bypass_mode: Cloudflare bypass 方式，可选值为 'html'、'mirror' 或 None

    Returns:
        requests.Response对象
    """
    bypass_mode = kwargs.pop('bypass_mode', None)

    if bypass_mode:
        headers = kwargs.get('headers')

        if bypass_mode == "html":
            return _cloudflare_bypass_client.html(url=url, headers=headers)  # type: ignore
        elif bypass_mode == "mirror":
            return _cloudflare_bypass_client.mirror(url=url, headers=headers)  # type: ignore
        else:
            raise ValueError(f"无效的 Cloudflare bypass 类型: {bypass_mode}，应为 'html' 或 'mirror'")
    else:
        session = requests.Session()

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

        from .proxy_provider import get_proxy_provider
        proxy_provider = get_proxy_provider()
        domain = _extract_domain(url)

        return _request_with_proxy_rotation(
            lambda attempt_kwargs: session.request(method, url, **attempt_kwargs),
            proxy_provider=proxy_provider,
            domain=domain,
            base_kwargs=kwargs,
        )


def get(url: str, **kwargs):
    """
    发送GET请求（支持rate limiting和cloudflare bypass）

    Args:
        url: 目标URL
        **kwargs: 其他请求参数，包括可选的 bypass_mode 参数

    Kwargs:
        bypass_mode: Cloudflare bypass 方式，可选值为 'html'、'mirror' 或 None

    Returns:
        requests.Response对象
    """
    return request('GET', url, **kwargs)


def post(url: str, **kwargs):
    """
    发送POST请求（支持rate limiting和cloudflare bypass）

    Args:
        url: 目标URL
        **kwargs: 其他请求参数，包括可选的 bypass_mode 参数

    Kwargs:
        bypass_mode: Cloudflare bypass 方式，可选值为 'html'、'mirror' 或 None

    Returns:
        requests.Response对象
    """
    return request('POST', url, **kwargs)


_cloudflare_bypass_client: Optional[object] = None


def configure_cloudflare_bypass_client(client: object) -> None:
    """配置 Cloudflare bypass 客户端（由后端注入）"""
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client
    logger.info("Cloudflare bypass client configured")

