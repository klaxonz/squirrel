import logging
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError
from urllib3.util.retry import Retry

from utils.rate_limiter import rate_limiter

logger = logging.getLogger()


DEFAULT_TIMEOUT_SECONDS = 20


class RateLimitAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        # 允许外部传入 pool_connections、pool_maxsize 等参数
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """Send request with rate limiting and logging"""
        try:
            domain = urlparse(request.url).netloc.replace('www.', '')
            rate_limiter.wait(domain)
            # 统一默认超时（显式传入的超时优先生效）
            if 'timeout' not in kwargs or kwargs.get('timeout') is None:
                kwargs['timeout'] = DEFAULT_TIMEOUT_SECONDS
            response = super().send(request, **kwargs)

            return response

        except (RequestException, HTTPError) as e:
            raise


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

        # 扩大连接池，提升并发场景下的复用能力
        adapter = RateLimitAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def request(self, method: str, url: str, **kwargs):
        # 兜底默认超时，个别调用点仍可通过传参覆盖
        kwargs.setdefault('timeout', DEFAULT_TIMEOUT_SECONDS)
        return super().request(method, url, **kwargs)


session = Session()
