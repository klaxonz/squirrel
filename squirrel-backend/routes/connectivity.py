"""站点连通性测试路由
提供站点可访问性检测、响应时间测量等功能
"""
import asyncio
import inspect
import logging
import socket
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, status

from schemas.connectivity import (
    BatchConnectivityTestRequest,
    BatchConnectivityTestResponse,
    ConnectivityTestRequest,
    ConnectivityTestResponse,
)
from utils.runtime_http import get_cloudflare_bypass_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connectivity", tags=["Connectivity"])

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

AGGRESSIVE_HEADER_EXTRAS = {
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}

RESTRICTED_STATUS_CODES = {401, 403, 406, 409, 412, 429}


async def _await_if_needed(result):
    if inspect.isawaitable(result):
        return await result
    return result


def build_browser_headers(target_url: str, aggressive: bool = False) -> dict[str, str]:
    headers = dict(BROWSER_HEADERS)
    parsed = urlparse(target_url)
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers.setdefault("Referer", origin + "/")
        headers.setdefault("Origin", origin)
    if aggressive:
        headers.update(AGGRESSIVE_HEADER_EXTRAS)
    return headers


async def fetch_with_fallback(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response:
    response = await client.get(url, headers=build_browser_headers(url))
    if response.status_code in RESTRICTED_STATUS_CODES:
        logger.info("Site %s returned restricted status %s, retrying with aggressive headers", url, response.status_code)
        fallback_response = await client.get(url, headers=build_browser_headers(url, aggressive=True))
        if fallback_response.status_code not in RESTRICTED_STATUS_CODES:
            logger.info("Aggressive headers resolved restriction for %s", url)
            return fallback_response
        bypass_response = await _fetch_with_cloudflare_bypass(url)
        if bypass_response is not None and bypass_response.status_code not in RESTRICTED_STATUS_CODES:
            logger.info("Cloudflare bypass resolved restriction for %s", url)
            return bypass_response
        response = fallback_response
    return response


async def _fetch_with_cloudflare_bypass(url: str):
    client = get_cloudflare_bypass_client()
    if client is None:
        return None

    headers = build_browser_headers(url, aggressive=True)
    try:
        return await _await_if_needed(client.html(url, headers=headers))
    except Exception as exc:
        # task boundary -- prevent single failure from crashing request
        logger.warning("Cloudflare bypass connectivity test failed for %s: %s", url, exc)
        return None


async def test_site_connectivity(
    url: str,
    timeout: int = 10,
    follow_redirects: bool = True,
) -> ConnectivityTestResponse:
    """测试单个站点的连通性

    Args:
        url: 要测试的URL
        timeout: 超时时间（秒）
        follow_redirects: 是否跟随重定向

    Returns:
        ConnectivityTestResponse: 测试结果

    """
    start_time = time.time()
    result = ConnectivityTestResponse(
        url=url,
        status="unknown",
        accessible=False,
    )

    try:
        # 尝试解析域名
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if hostname:
            try:
                ip_address = socket.gethostbyname(hostname)
                result.dns_resolved = True
                result.ip_address = ip_address
                logger.info(f"DNS resolved for {hostname}: {ip_address}")
            except socket.gaierror as e:
                result.dns_resolved = False
                result.status = "error"
                result.error_message = f"DNS解析失败: {e!s}"
                logger.warning(f"DNS resolution failed for {hostname}: {e}")
                return result

        # 发起HTTP请求
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            verify=False,  # 忽略SSL证书验证，避免自签名证书导致的连接失败
        ) as client:
            try:
                response = await fetch_with_fallback(client, url)
                response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                result.status_code = response.status_code
                result.response_time = round(response_time, 2)
                result.final_url = str(response.url)

                # 提取部分响应头
                result.headers = {
                    "content-type": response.headers.get("content-type", ""),
                    "server": response.headers.get("server", ""),
                    "content-length": response.headers.get("content-length", ""),
                }

                # 判断是否可访问（2xx 和 3xx 状态码都认为是成功）
                if 200 <= response.status_code < 400:
                    result.status = "success"
                    result.accessible = True
                    logger.info(f"Site {url} is accessible, status: {response.status_code}, time: {response_time:.2f}ms")
                elif response.status_code in RESTRICTED_STATUS_CODES:
                    result.status = "restricted"
                    result.accessible = True
                    result.error_message = f"站点响应限制HTTP状态码: {response.status_code}"
                    logger.info(f"Site {url} responded with restricted status {response.status_code} but is reachable")
                else:
                    result.status = "failed"
                    result.accessible = False
                    result.error_message = f"HTTP状态码: {response.status_code}"
                    logger.warning(f"Site {url} returned status {response.status_code}")

            except httpx.TimeoutException as e:
                result.status = "timeout"
                result.accessible = False
                result.error_message = f"请求超时（{timeout}秒）"
                logger.warning(f"Timeout testing {url}: {e}")

            except httpx.ConnectError as e:
                result.status = "error"
                result.accessible = False
                result.error_message = f"连接失败: {e!s}"
                logger.warning(f"Connection error testing {url}: {e}")

            except httpx.HTTPError as e:
                result.status = "error"
                result.accessible = False
                result.error_message = f"HTTP错误: {e!s}"
                logger.warning(f"HTTP error testing {url}: {e}")

    except Exception as e:
        # task boundary -- prevent single failure from crashing request
        result.status = "error"
        result.accessible = False
        result.error_message = f"未知错误: {e!s}"
        logger.error(f"Unexpected error testing {url}: {e}", exc_info=True)

    return result


@router.post("/test", response_model=ConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_connectivity(request: ConnectivityTestRequest) -> ConnectivityTestResponse:
    """测试单个站点的连通性

    Args:
        request: 连通性测试请求

    Returns:
        ConnectivityTestResponse: 测试结果

    """
    logger.info(f"Testing connectivity for: {request.url}")

    result = await test_site_connectivity(
        url=request.url,
        timeout=request.timeout,
        follow_redirects=request.follow_redirects,
    )

    return result


@router.post("/test/batch", response_model=BatchConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_batch_connectivity(request: BatchConnectivityTestRequest) -> BatchConnectivityTestResponse:
    """批量测试多个站点的连通性

    Args:
        request: 批量连通性测试请求

    Returns:
        BatchConnectivityTestResponse: 批量测试结果

    """
    logger.info(f"Testing batch connectivity for {len(request.urls)} URLs")

    # 并发测试所有URL
    tasks = [
        test_site_connectivity(
            url=url,
            timeout=request.timeout,
            follow_redirects=request.follow_redirects,
        )
        for url in request.urls
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                ConnectivityTestResponse(
                    url=request.urls[i],
                    status="error",
                    accessible=False,
                    error_message=str(result),
                ),
            )
        else:
            processed_results.append(result)

    # 生成汇总信息
    total = len(processed_results)
    accessible_count = sum(1 for r in processed_results if r.accessible)
    failed_count = sum(1 for r in processed_results if not r.accessible)
    avg_response_time = None

    response_times = [r.response_time for r in processed_results if r.response_time is not None]
    if response_times:
        avg_response_time = round(sum(response_times) / len(response_times), 2)

    summary = {
        "total": total,
        "accessible": accessible_count,
        "failed": failed_count,
        "success_rate": round(accessible_count / total * 100, 2) if total > 0 else 0,
        "avg_response_time": avg_response_time,
    }

    logger.info(f"Batch test completed: {accessible_count}/{total} sites accessible")

    return BatchConnectivityTestResponse(
        results=processed_results,
        summary=summary,
    )


@router.get("/test/quick", status_code=status.HTTP_200_OK)
async def quick_test(url: str) -> dict[str, Any]:
    """快速测试站点连通性（简化版本）

    Args:
        url: 要测试的URL

    Returns:
        简化的测试结果

    """
    logger.info(f"Quick testing: {url}")

    # 确保URL格式正确
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = await test_site_connectivity(url, timeout=5, follow_redirects=True)

    return {
        "url": result.url,
        "accessible": result.accessible,
        "status": result.status,
        "response_time": result.response_time,
        "error": result.error_message,
    }
