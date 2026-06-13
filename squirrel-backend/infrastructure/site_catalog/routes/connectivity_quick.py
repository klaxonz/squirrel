import logging
from typing import Any

from fastapi import APIRouter, status

from infrastructure.site_catalog.connectivity import test_site_connectivity

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/test/quick', status_code=status.HTTP_200_OK)
async def quick_test(url: str) -> dict[str, Any]:
    """Quick test site connectivity."""
    logger.info('Quick testing: %s', url)

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    test_result = await test_site_connectivity(url, timeout=5, follow_redirects=True)

    return {
        'url': test_result.url,
        'accessible': test_result.accessible,
        'status': test_result.status,
        'response_time': test_result.response_time,
        'error': test_result.error_message,
    }
