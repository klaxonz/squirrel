import logging
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.rate_limiter import rate_limiter

logger = logging.getLogger()


class RateLimitAdapter(HTTPAdapter):
    """HTTP adapter that implements rate limiting"""

    def send(self, request, **kwargs):
        """Send request with rate limiting"""
        # Extract domain from request URL
        domain = urlparse(request.url).netloc.replace('www.', '')
        # Apply rate limiting
        rate_limiter.wait(domain)
        return super().send(request, **kwargs)


class Session(requests.Session):
    def __init__(self, retries: int = 3, backoff_factor: float = 0.3):
        super().__init__()

        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 504),
        )

        # Use our custom rate limiting adapter
        adapter = RateLimitAdapter(max_retries=retry)
        self.mount("http://", adapter)
        self.mount("https://", adapter)


# Global session instance
session = Session()
