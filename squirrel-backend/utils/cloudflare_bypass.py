import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urljoin
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
        cookies: Optional[str] = None,
        follow_redirects: bool = True,
        max_redirects: int = 5
    ) -> CloudflareBypassResult:
        try:
            result = self._fetch_with_redirects(
                url=url,
                cookies=cookies,
                follow_redirects=follow_redirects,
                max_redirects=max_redirects
            )

            if not result.success and "HTTP 403" in (result.error or ""):
                logger.info(f"镜像返回 403，尝试使用 /html 端点")
                start_time = time.time()

                headers = {}
                if cookies:
                    headers["Cookie"] = cookies

                try:
                    response = requests.get(
                        f"{self.service_url}/html",
                        params={"url": url},
                        headers=headers,
                        timeout=self.timeout,
                        allow_redirects=False
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

            return result
        except Exception as e:
            logger.error(f"Cloudflare bypass 请求失败: {e}")
            return CloudflareBypassResult(
                success=False,
                error=str(e),
                final_url=url
            )

    def _fetch_with_redirects(
        self,
        url: str,
        cookies: Optional[str],
        follow_redirects: bool,
        max_redirects: int
    ) -> CloudflareBypassResult:
        current_url = url
        redirect_count = 0
        start_time = time.time()

        while redirect_count <= max_redirects:
            parsed = urlparse(current_url)
            hostname = parsed.netloc
            path = parsed.path + ('?' + parsed.query if parsed.query else '')

            headers = {"x-hostname": hostname}
            if cookies:
                headers["Cookie"] = cookies

            try:
                response = requests.get(
                    f"{self.service_url}{path}",
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=False
                )
            except requests.RequestException as e:
                elapsed = time.time() - start_time
                return CloudflareBypassResult(
                    success=False,
                    error=f"请求异常: {str(e)}",
                    final_url=current_url,
                    redirect_count=redirect_count,
                    elapsed=elapsed
                )

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')

                if not location:
                    import re
                    match = re.search(r'href="([^"]+)"', response.text)
                    if match:
                        location = match.group(1)
                    else:
                        elapsed = time.time() - start_time
                        return CloudflareBypassResult(
                            success=False,
                            error="重定向响应缺少 Location header",
                            html=response.text,
                            final_url=current_url,
                            redirect_count=redirect_count,
                            elapsed=elapsed
                        )

                next_url = location if location.startswith('http') else urljoin(current_url, location)

                if not follow_redirects:
                    elapsed = time.time() - start_time
                    return CloudflareBypassResult(
                        success=False,
                        error=f"遇到重定向但未启用自动跟随: {next_url}",
                        final_url=next_url,
                        redirect_count=redirect_count,
                        elapsed=elapsed
                    )

                current_url = next_url
                redirect_count += 1
                continue

            if response.status_code == 200:
                elapsed = time.time() - start_time
                return CloudflareBypassResult(
                    success=True,
                    html=response.text,
                    final_url=current_url,
                    redirect_count=redirect_count,
                    elapsed=elapsed
                )
            else:
                elapsed = time.time() - start_time
                return CloudflareBypassResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    final_url=current_url,
                    redirect_count=redirect_count,
                    elapsed=elapsed
                )

        elapsed = time.time() - start_time
        return CloudflareBypassResult(
            success=False,
            error=f"超过最大重定向次数: {max_redirects}",
            final_url=current_url,
            redirect_count=redirect_count,
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
    cookies: Optional[str] = None,
    follow_redirects: bool = True,
    max_redirects: int = 5
) -> CloudflareBypassResult:
    client = get_default_client()
    return client.fetch(
        url=url,
        cookies=cookies,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects
    )
