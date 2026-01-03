import logging
import time
from dataclasses import dataclass
from typing import Optional
import requests

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CloudflareBypassResult:
    success: bool
    final_url: str
    html: Optional[str] = None
    error: Optional[str] = None
    redirect_count: int = 0
    elapsed: float = 0.0


class CloudflareMirrorClient:
    def __init__(self, service_url: str, timeout: int = 120):
        if not service_url:
            raise ValueError("service_url 不能为空")
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout

    def fetch(
        self,
        url: str,
        headers: Optional[dict] = None,
        follow_redirects: bool = True,
        max_redirects: int = 5
    ) -> CloudflareBypassResult:
        start_time = time.time()
        request_headers = headers.copy() if headers else {}

        try:
            response = requests.get(
                f"{self.service_url}/html",
                params={"url": url},
                headers=request_headers,
                timeout=self.timeout,
                allow_redirects=True
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                return CloudflareBypassResult(
                    success=True,
                    html=response.text,
                    final_url=url,
                    elapsed=elapsed
                )
            else:
                return CloudflareBypassResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    final_url=url,
                    elapsed=elapsed
                )
        except requests.RequestException as e:
            elapsed = time.time() - start_time
            return CloudflareBypassResult(
                success=False,
                error=f"请求异常: {str(e)}",
                final_url=url,
                elapsed=elapsed
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Cloudflare bypass 请求失败: {e}")
            return CloudflareBypassResult(
                success=False,
                error=str(e),
                final_url=url,
                elapsed=elapsed
            )

    def clear_cache(self):
        try:
            response = requests.post(
                f"{self.service_url}/cache/clear",
                timeout=self.timeout
            )
        except requests.RequestException as e:
            logger.error(e)

_default_client: Optional[CloudflareMirrorClient] = None


def get_default_client() -> CloudflareMirrorClient:
    global _default_client
    if _default_client is None:
        service_url = settings.CLOUDFLARE_BYPASS_SERVICE_URL
        if not service_url:
            raise ValueError("配置项 CLOUDFLARE_BYPASS_SERVICE_URL 未设置")
        _default_client = CloudflareMirrorClient(service_url)
    return _default_client


def fetch_with_bypass(
    url: str,
    headers: Optional[dict] = None,
    follow_redirects: bool = True,
    max_redirects: int = 5
) -> CloudflareBypassResult:
    client = get_default_client()
    return client.fetch(
        url=url,
        headers=headers,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects
    )
