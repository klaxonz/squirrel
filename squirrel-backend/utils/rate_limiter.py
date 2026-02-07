import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Set

from .url_helper import extract_second_level_domain

logger = logging.getLogger()


@dataclass
class RateLimit:
    """Rate limit configuration"""
    min_interval: float  # Minimum interval between requests
    max_interval: float  # Maximum interval between requests
    domain: str  # Domain this rate limit applies to


class RateLimiter:
    """Rate limiter to prevent too frequent requests

    目标：
    - 线程安全：对每个二级域名使用独立锁，避免竞争条件
    - 分桶：未知域名不再共用全局 '*' 桶，而是各自以二级域名为桶键
    """

    # Site-specific defaults are driven by site configs; keep the map empty here
    DEFAULT_LIMITS: Dict[str, RateLimit] = {}

    # Global default rate limit config (used for unknown domains)
    DEFAULT_RATE_LIMIT = RateLimit(3, 5, '*')

    def __init__(self):
        # key: second-level domain, value: last request timestamp
        self._last_request_time: Dict[str, float] = {}
        # key: second-level domain, value: RateLimit
        self._rate_limits: Dict[str, RateLimit] = self.DEFAULT_LIMITS.copy()
        self._disabled_domains: Set[str] = set()
        # per-domain locks to ensure thread safety per bucket
        self._domain_locks: Dict[str, threading.Lock] = {}
        # protect maps for lazy lock creation
        self._locks_map_lock = threading.Lock()

    def add_rate_limit(self, domain: str, min_interval: float, max_interval: float):
        """Add or update rate limit for a domain (expects second-level domain)"""
        sld = extract_second_level_domain(domain)
        self._disabled_domains.discard(sld)
        self._rate_limits[sld] = RateLimit(min_interval, max_interval, sld)

    def set_domain_enabled(self, domain: str, enabled: bool):
        sld = extract_second_level_domain(domain)
        if not sld:
            return
        if enabled:
            self._disabled_domains.discard(sld)
            return
        self._disabled_domains.add(sld)

    def _get_lock(self, sld: str) -> threading.Lock:
        # lazy create lock per domain
        lock = self._domain_locks.get(sld)
        if lock is None:
            with self._locks_map_lock:
                lock = self._domain_locks.get(sld)
                if lock is None:
                    lock = threading.Lock()
                    self._domain_locks[sld] = lock
        return lock

    def wait(self, domain: Optional[str] = None):
        """Wait according to rate limit per second-level domain"""
        sld = extract_second_level_domain(domain) if domain else '*'
        if sld in self._disabled_domains:
            return

        # choose rate limit config
        rate_limit = self._rate_limits.get(sld, self.DEFAULT_RATE_LIMIT)

        # unknown domains should still have independent buckets keyed by sld
        bucket_key = sld if sld and sld != '' else '*'
        lock = self._get_lock(bucket_key)

        with lock:
            last_time = self._last_request_time.get(bucket_key, 0.0)

            # Calculate time to wait
            now = time.time()
            elapsed = now - last_time
            interval = random.uniform(rate_limit.min_interval, rate_limit.max_interval)

            if elapsed < interval:
                time.sleep(interval - elapsed)

            # update last request time for this bucket
            self._last_request_time[bucket_key] = time.time()


# Global rate limiter instance
rate_limiter = RateLimiter()
