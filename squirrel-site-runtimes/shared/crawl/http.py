"""HTTP utilities with shared rate-limited session for plugins."""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 20


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    netloc = parsed.netloc if parsed.netloc else url
    host = netloc.split(":", 1)[0]
    domain = host.replace("www.", "")
    return domain or None


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


class RateLimiter:
    def __init__(
        self,
        default_limit: RateLimit | None = None,
        domain_limits: dict[str, RateLimit] | None = None,
    ) -> None:
        self._default_limit = default_limit or RateLimit(3, 5, "*")
        provided_limits = domain_limits or {}
        self._rate_limits: dict[str, RateLimit] = dict(provided_limits)
        self._last_request_time: dict[str, float] = {}
        self._disabled_domains: set[str] = set()
        self._locks: dict[str, threading.Lock] = {}
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

    def get_rate_limit(self, domain: str | None) -> RateLimit:
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

    def wait(self, domain: str | None = None) -> None:
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
        rate_limiter: RateLimiter | None = None,
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
        return super().request(method, url, **kwargs)


_default_rate_limiter = RateLimiter()
_shared_session: RateLimitedSession | None = None
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


def _resolve_maybe_async_result(result):
    if not inspect.isawaitable(result):
        return result

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(result)

    outcome: dict[str, object] = {}

    def _runner() -> None:
        try:
            outcome["value"] = asyncio.run(result)
        except BaseException as exc:  # pragma: no cover - defensive bridge
            outcome["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    error = outcome.get("error")
    if error is not None:
        raise error  # type: ignore[misc]
    return outcome.get("value")


def request(method: str, url: str, **kwargs):
    """Send an HTTP request with rate limiting and optional Cloudflare bypass.

    Args:
        method: HTTP method.
        url: Target URL.
        **kwargs: Additional request parameters, including optional ``bypass_mode``.

    Kwargs:
        bypass_mode: Cloudflare bypass mode — ``'html'``, ``'mirror'``, or ``None``.

    Returns:
        ``requests.Response``.
    """
    use_cloudflare_bypass = kwargs.pop("bypass_mode", None)

    if use_cloudflare_bypass:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "") if parsed.netloc else url

        _default_rate_limiter.wait(domain)

        headers = kwargs.get("headers")

        if use_cloudflare_bypass == "html":
            return _resolve_maybe_async_result(_cloudflare_bypass_client.html(url=url, headers=headers))  # type: ignore
        elif use_cloudflare_bypass == "mirror":
            return _resolve_maybe_async_result(_cloudflare_bypass_client.mirror(url=url, headers=headers))  # type: ignore
        else:
            raise ValueError(f"无效的 Cloudflare bypass 类型: {use_cloudflare_bypass}，应为 'html' 或 'mirror'")
    else:
        session = get_http_session()
        return session.request(method, url, **kwargs)


def request_without_limit(method: str, url: str, **kwargs):
    """Send an HTTP request without rate limiting (supports Cloudflare bypass).

    Args:
        method: HTTP method.
        url: Target URL.
        **kwargs: Additional request parameters, including optional ``bypass_mode``.

    Kwargs:
        bypass_mode: Cloudflare bypass mode — ``'html'``, ``'mirror'``, or ``None``.

    Returns:
        ``requests.Response``.
    """
    bypass_mode = kwargs.pop("bypass_mode", None)

    if bypass_mode:
        headers = kwargs.get("headers")

        if bypass_mode == "html":
            return _resolve_maybe_async_result(_cloudflare_bypass_client.html(url=url, headers=headers))  # type: ignore
        elif bypass_mode == "mirror":
            return _resolve_maybe_async_result(_cloudflare_bypass_client.mirror(url=url, headers=headers))  # type: ignore
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
        return session.request(method, url, **kwargs)


def get(url: str, **kwargs):
    """Send a GET request with rate limiting and optional Cloudflare bypass.

    Args:
        url: Target URL.
        **kwargs: Additional request parameters, including optional ``bypass_mode``.

    Kwargs:
        bypass_mode: Cloudflare bypass mode — ``'html'``, ``'mirror'``, or ``None``.

    Returns:
        ``requests.Response``.
    """
    return request("GET", url, **kwargs)


def post(url: str, **kwargs):
    """Send a POST request with rate limiting and optional Cloudflare bypass.

    Args:
        url: Target URL.
        **kwargs: Additional request parameters, including optional ``bypass_mode``.

    Kwargs:
        bypass_mode: Cloudflare bypass mode — ``'html'``, ``'mirror'``, or ``None``.

    Returns:
        ``requests.Response``.
    """
    return request("POST", url, **kwargs)


_cloudflare_bypass_client: object | None = None


def configure_cloudflare_bypass_client(client: object) -> None:
    """Configure a Cloudflare bypass client (injected by the backend)."""
    global _cloudflare_bypass_client
    _cloudflare_bypass_client = client
    logger.info("Cloudflare bypass client configured")


def _reset_http_module_state() -> None:
    """Reset all module-level state to defaults (test isolation)."""
    global _default_rate_limiter, _shared_session, _cloudflare_bypass_client
    _default_rate_limiter = RateLimiter()
    _shared_session = None
    _cloudflare_bypass_client = None

