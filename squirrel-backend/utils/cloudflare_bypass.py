import logging
from typing import Optional
import requests
from core.config import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CloudflareMirrorClient:
    def __init__(self, service_url: str, timeout: int = 120):
        if not service_url:
            raise ValueError("service_url 不能为空")
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout

    def html(
        self,
        url: str,
        headers: Optional[dict] = None
    ):
        request_headers = headers.copy() if headers else {}

        return requests.get(
            f"{self.service_url}/html",
            params={"url": url},
            headers=request_headers,
            timeout=self.timeout,
            allow_redirects=True
        )

    def mirror(
        self,
        url: str,
        headers: Optional[dict] = None
    ):
        request_headers = headers.copy() if headers else {}
        parsed_url = urlparse(url)
        path = parsed_url.path.lstrip("/")

        host = parsed_url.netloc
        host = host.split(":")[0]

        url = f"{self.service_url}/{path}"

        headers = {
            "x-hostname": host,
        }
        headers.update(request_headers)

        return requests.get(
            url,
            headers=headers,
            timeout=self.timeout,
            allow_redirects=True
        )


    def clear_cache(self):
        return requests.post(
            f"{self.service_url}/cache/clear",
            timeout=self.timeout
        )


_default_client: Optional[CloudflareMirrorClient] = None


def get_default_client() -> CloudflareMirrorClient:
    global _default_client
    if _default_client is None:
        service_url = settings.CLOUDFLARE_BYPASS_SERVICE_URL
        if not service_url:
            raise ValueError("配置项 CLOUDFLARE_BYPASS_SERVICE_URL 未设置")
        _default_client = CloudflareMirrorClient(service_url)
    return _default_client


