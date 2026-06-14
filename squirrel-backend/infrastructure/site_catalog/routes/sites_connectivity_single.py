from fastapi import APIRouter, Depends, Query

from infrastructure.site_catalog.connectivity import test_site_connectivity
from infrastructure.site_catalog.routes.sites_dependencies import get_catalog_service
from infrastructure.site_catalog.service import SiteCatalogService
from shared_kernel.application.response import error, param_error, success

router = APIRouter()


@router.get('/{site_name}/test-connectivity')
async def test_site_connectivity_endpoint(
    site_name: str,
    timeout: int = Query(10, ge=1, le=60),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    site_info = catalog_svc.build_site_info(site_name, catalog)

    if not site_info:
        return param_error(f'Unsupported site: {site_name}')

    site_domains = site_info.get('domains') or []
    test_url = site_info.get('test_url')

    if not site_domains and not test_url:
        return error(f'Site {site_name} has no associated domains')
    if not test_url:
        return error(f'Site {site_name} has no configured test URL')

    connectivity_result = await test_site_connectivity(
        url=test_url,
        timeout=timeout,
        follow_redirects=True,
    )

    return success({
        'site_name': site_name,
        'domains': site_domains,
        'test_url': connectivity_result.url,
        'accessible': connectivity_result.accessible,
        'status': connectivity_result.status,
        'status_code': connectivity_result.status_code,
        'response_time': connectivity_result.response_time,
        'dns_resolved': connectivity_result.dns_resolved,
        'ip_address': connectivity_result.ip_address,
        'error_message': connectivity_result.error_message,
    })
