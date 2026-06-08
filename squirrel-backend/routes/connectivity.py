"""Site connectivity test routes
Provides site accessibility detection, response time measurement, etc.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, status

from schemas.connectivity import (
    BatchConnectivityTestRequest,
    BatchConnectivityTestResponse,
    ConnectivityTestRequest,
    ConnectivityTestResponse,
)
from services.connectivity_service import test_site_connectivity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connectivity", tags=["Connectivity"])


@router.post("/test", response_model=ConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_connectivity(request: ConnectivityTestRequest) -> ConnectivityTestResponse:
    """Test connectivity of a single site

    Args:
        request: Connectivity test request

    Returns:
        ConnectivityTestResponse: Test result

    """
    logger.info("Testing connectivity for: %s", request.url)

    test_result = await test_site_connectivity(
        url=request.url,
        timeout=request.timeout,
        follow_redirects=request.follow_redirects,
    )

    return test_result


@router.post("/test/batch", response_model=BatchConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_batch_connectivity(request: BatchConnectivityTestRequest) -> BatchConnectivityTestResponse:
    """Test connectivity of multiple sites in batch

    Args:
        request: Batch connectivity test request

    Returns:
        BatchConnectivityTestResponse: Batch test result

    """
    logger.info("Testing batch connectivity for %s URLs", len(request.urls))

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

    logger.info("Batch test completed: %s/%s sites accessible", accessible_count, total)

    return BatchConnectivityTestResponse(
        results=processed_results,
        summary=summary,
    )


@router.get("/test/quick", status_code=status.HTTP_200_OK)
async def quick_test(url: str) -> dict[str, Any]:
    """Quick test site connectivity (simplified version)

    Args:
        url: The URL to test

    Returns:
        Simplified test result

    """
    logger.info("Quick testing: %s", url)

    # 确保URL格式正确
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    test_result = await test_site_connectivity(url, timeout=5, follow_redirects=True)

    return {
        "url": test_result.url,
        "accessible": test_result.accessible,
        "status": test_result.status,
        "response_time": test_result.response_time,
        "error": test_result.error_message,
    }
