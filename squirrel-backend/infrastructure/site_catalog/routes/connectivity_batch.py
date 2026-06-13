import asyncio
import logging

from fastapi import APIRouter, status

from infrastructure.site_catalog.connectivity import (
    BatchConnectivityTestRequest,
    BatchConnectivityTestResponse,
    ConnectivityTestResponse,
    test_site_connectivity,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/test/batch', response_model=BatchConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_batch_connectivity(request: BatchConnectivityTestRequest) -> BatchConnectivityTestResponse:
    """Test connectivity of multiple sites in batch."""
    logger.info('Testing batch connectivity for %s URLs', len(request.urls))

    tasks = [
        test_site_connectivity(
            url=url,
            timeout=request.timeout,
            follow_redirects=request.follow_redirects,
        )
        for url in request.urls
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                ConnectivityTestResponse(
                    url=request.urls[i],
                    status='error',
                    accessible=False,
                    error_message=str(result),
                ),
            )
        else:
            processed_results.append(result)

    total = len(processed_results)
    accessible_count = sum(1 for r in processed_results if r.accessible)
    failed_count = sum(1 for r in processed_results if not r.accessible)
    avg_response_time = None

    response_times = [r.response_time for r in processed_results if r.response_time is not None]
    if response_times:
        avg_response_time = round(sum(response_times) / len(response_times), 2)

    summary = {
        'total': total,
        'accessible': accessible_count,
        'failed': failed_count,
        'success_rate': round(accessible_count / total * 100, 2) if total > 0 else 0,
        'avg_response_time': avg_response_time,
    }

    logger.info('Batch test completed: %s/%s sites accessible', accessible_count, total)

    return BatchConnectivityTestResponse(
        results=processed_results,
        summary=summary,
    )
