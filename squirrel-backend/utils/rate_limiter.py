import logging
import random
import time
import threading
from dataclasses import dataclass
from typing import Optional, Dict
from urllib.parse import urlparse

logger = logging.getLogger()


def extract_second_level_domain(domain_or_url: str) -> str:
    """Extract second level domain from URL or domain string
    
    Examples:
        'https://www.example.com/path' -> 'example.com'
        'api.example.com' -> 'example.com'
        'example.com' -> 'example.com'
        'sub.domain.example.com' -> 'example.com'
    """
    if not domain_or_url:
        return domain_or_url
    
    # Handle URLs by extracting hostname first
    if '://' in domain_or_url:
        parsed = urlparse(domain_or_url)
        domain = parsed.hostname or domain_or_url
    else:
        domain = domain_or_url
    
    # Split domain parts
    parts = domain.lower().split('.')
    
    # Return last two parts for second level domain
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    
    return domain


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

    # Default rate limits for different domains (second-level domains)
    DEFAULT_LIMITS: Dict[str, RateLimit] = {
        'bilibili.com': RateLimit(3, 5, 'bilibili.com'),
        'youtube.com': RateLimit(2, 5, 'youtube.com'),
        'pornhub.com': RateLimit(3, 8, 'pornhub.com'),
        'javdb.com': RateLimit(5, 8, 'javdb.com'),  # javdb 需要更长的间隔避免风控
    }

    # Global default rate limit config (used for unknown domains)
    DEFAULT_RATE_LIMIT = RateLimit(3, 5, '*')

    def __init__(self):
        # key: second-level domain, value: last request timestamp
        self._last_request_time: Dict[str, float] = {}
        # key: second-level domain, value: RateLimit
        self._rate_limits: Dict[str, RateLimit] = self.DEFAULT_LIMITS.copy()
        # per-domain locks to ensure thread safety per bucket
        self._domain_locks: Dict[str, threading.Lock] = {}
        # protect maps for lazy lock creation
        self._locks_map_lock = threading.Lock()

    def add_rate_limit(self, domain: str, min_interval: float, max_interval: float):
        """Add or update rate limit for a domain (expects second-level domain)"""
        sld = extract_second_level_domain(domain)
        self._rate_limits[sld] = RateLimit(min_interval, max_interval, sld)

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
