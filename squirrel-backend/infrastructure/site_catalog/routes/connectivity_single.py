import logging

from fastapi import APIRouter, status

from infrastructure.site_catalog.connectivity import ConnectivityTestRequest, ConnectivityTestResponse, test_site_connectivity

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/test', response_model=ConnectivityTestResponse, status_code=status.HTTP_200_OK)
async def test_connectivity(request: ConnectivityTestRequest) -> ConnectivityTestResponse:
    """Test connectivity of a single site."""
    logger.info('Testing connectivity for: %s', request.url)

    return await test_site_connectivity(
        url=request.url,
        timeout=request.timeout,
        follow_redirects=request.follow_redirects,
    )
