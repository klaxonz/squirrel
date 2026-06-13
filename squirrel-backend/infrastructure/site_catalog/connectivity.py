"""Site connectivity service - provides site accessibility detection, response time measurement, etc.
"""
import logging
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, field_validator


class ConnectivityTestRequest(BaseModel):
    """Connectivity test request model"""

    url: str = Field(..., description="URL to test")
    timeout: int | None = Field(10, description="Timeout (seconds), default 10s", ge=1, le=60)
    follow_redirects: bool | None = Field(True, description="Whether to follow redirects")

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("URL must not be empty")

        v_str = str(v).strip()

        # Auto-add https:// if no protocol specified
        if not v_str.startswith(("http://", "https://")):
            v_str = "https://" + v_str

        try:
            parsed = urlparse(v_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL format")

        return v_str


class ConnectivityTestResponse(BaseModel):
    """Connectivity test response model"""

    url: str = Field(..., description="Tested URL")
    status: str = Field(..., description="Test status: success, failed, timeout, error")
    accessible: bool = Field(..., description="Whether accessible")
    status_code: int | None = Field(None, description="HTTP status code")
    response_time: float | None = Field(None, description="Response time (ms)")
    final_url: str | None = Field(None, description="Final URL (if redirected)")
    error_message: str | None = Field(None, description="Error message")
    dns_resolved: bool | None = Field(None, description="Whether DNS resolved successfully")
    ip_address: str | None = Field(None, description="Resolved IP address")
    headers: dict[str, str] | None = Field(None, description="Response headers")


class BatchConnectivityTestRequest(BaseModel):
    """Batch connectivity test request model"""

    urls: list[str] = Field(..., description="URLs to test", min_length=1, max_length=20)
    timeout: int | None = Field(10, description="Timeout (seconds), default 10s", ge=1, le=60)
    follow_redirects: bool | None = Field(True, description="Whether to follow redirects")


class BatchConnectivityTestResponse(BaseModel):
    """Batch connectivity test response model"""

    results: list[ConnectivityTestResponse] = Field(..., description="Test result list")
    summary: dict[str, Any] = Field(..., description="Summary information")


logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-CH-UA": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

RESTRICTED_STATUS_CODES = {401, 403, 406, 409, 412, 429}


def build_browser_headers(target_url: str) -> dict[str, str]:
    headers = dict(BROWSER_HEADERS)
    parsed = urlparse(target_url)
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers.setdefault("Referer", origin + "/")
        headers.setdefault("Origin", origin)
    return headers


async def fetch_site_response(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response:
    return await client.get(url, headers=build_browser_headers(url))


async def test_site_connectivity(
    url: str,
    timeout: int = 10,
    follow_redirects: bool = True,
) -> ConnectivityTestResponse:
    """Test connectivity of a single site

    Args:
        url: The URL to test
        timeout: Timeout in seconds
        follow_redirects: Whether to follow redirects

    Returns:
        ConnectivityTestResponse: Test result

    """
    start_time = time.time()
    test_result = ConnectivityTestResponse(
        url=url,
        status="unknown",
        accessible=False,
    )

    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if hostname:
            try:
                ip_address = socket.gethostbyname(hostname)
                test_result.dns_resolved = True
                test_result.ip_address = ip_address
                logger.info("DNS resolved for %s: %s", hostname, ip_address)
            except socket.gaierror as e:
                test_result.dns_resolved = False
                test_result.status = "error"
                test_result.error_message = f"DNS解析失败: {e!s}"
                logger.warning("DNS resolution failed for %s: %s", hostname, e)
                return test_result

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify=False,
        ) as client:
            try:
                response = await fetch_site_response(client, url)
                response_time = (time.time() - start_time) * 1000

                test_result.status_code = response.status_code
                test_result.response_time = round(response_time, 2)
                test_result.final_url = str(response.url)

                test_result.headers = {
                    "content-type": response.headers.get("content-type", ""),
                    "server": response.headers.get("server", ""),
                    "content-length": response.headers.get("content-length", ""),
                }

                if 200 <= response.status_code < 400:
                    test_result.status = "success"
                    test_result.accessible = True
                    logger.info("Site %s is accessible, status: %s, time: %f'.2f'ms", url, response.status_code, response_time)
                elif response.status_code in RESTRICTED_STATUS_CODES:
                    test_result.status = "restricted"
                    test_result.accessible = True
                    test_result.error_message = f"站点响应限制HTTP状态码: {response.status_code}"
                    logger.info("Site %s responded with restricted status %s but is reachable", url, response.status_code)
                else:
                    test_result.status = "failed"
                    test_result.accessible = False
                    test_result.error_message = f"HTTP状态码: {response.status_code}"
                    logger.warning("Site %s returned status %s", url, response.status_code)

            except httpx.TimeoutException as e:
                test_result.status = "timeout"
                test_result.accessible = False
                test_result.error_message = f"请求超时（{timeout}秒）"
                logger.warning("Timeout testing %s: %s", url, e)

            except httpx.ConnectError as e:
                test_result.status = "error"
                test_result.accessible = False
                test_result.error_message = f"连接失败: {e!s}"
                logger.warning("Connection error testing %s: %s", url, e)

            except httpx.HTTPError as e:
                test_result.status = "error"
                test_result.accessible = False
                test_result.error_message = f"HTTP错误: {e!s}"
                logger.warning("HTTP error testing %s: %s", url, e)

    except Exception as e:
        test_result.status = "error"
        test_result.accessible = False
        test_result.error_message = f"未知错误: {e!s}"
        logger.error("Unexpected error testing %s: %s", url, e, exc_info=True)

    return test_result
