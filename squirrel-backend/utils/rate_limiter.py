import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimit:
    """Rate limit configuration"""
    min_interval: float  # Minimum interval between requests
    max_interval: float  # Maximum interval between requests
    domain: str         # Domain this rate limit applies to

class RateLimiter:
    """Rate limiter to prevent too frequent requests"""
    
    # Default rate limits for different domains
    DEFAULT_LIMITS = {
        'bilibili.com': RateLimit(3.0, 5.0, 'bilibili.com'),
        'youtube.com': RateLimit(2.0, 4.0, 'youtube.com'),
        'pornhub.com': RateLimit(3.0, 5.0, 'pornhub.com'),
        'javdb.com': RateLimit(3.0, 5.0, 'javdb.com'),
    }
    
    # Global default rate limit
    DEFAULT_RATE_LIMIT = RateLimit(2.0, 4.0, '*')
    
    def __init__(self):
        self._last_request_time: dict[str, float] = {}
        self._rate_limits: dict[str, RateLimit] = self.DEFAULT_LIMITS.copy()

    def add_rate_limit(self, domain: str, min_interval: float, max_interval: float):
        """Add or update rate limit for a domain"""
        self._rate_limits[domain] = RateLimit(min_interval, max_interval, domain)

    def wait(self, domain: Optional[str] = None):
        """Wait according to rate limit"""
        rate_limit = self._rate_limits.get(domain, self.DEFAULT_RATE_LIMIT)
        last_time = self._last_request_time.get(rate_limit.domain, 0)
        
        # Calculate time to wait
        now = time.time()
        elapsed = now - last_time
        interval = random.uniform(rate_limit.min_interval, rate_limit.max_interval)
        
        if elapsed < interval:
            time.sleep(interval - elapsed)
        
        self._last_request_time[rate_limit.domain] = time.time()

# Global rate limiter instance
rate_limiter = RateLimiter() 