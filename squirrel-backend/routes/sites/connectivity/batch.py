import asyncio

from fastapi import APIRouter, Depends, Query

from common.response import param_error, success
from routes.sites.dependencies import get_catalog_service
from services.site_catalog.connectivity import test_site_connectivity
from services.site_catalog.service import SiteCatalogService

router = APIRouter()


@router.post('/test-connectivity/batch')
async def test_batch_sites_connectivity(
    site_names: list[str] = Query(..., description='List of site names'),
    timeout: int = Query(10, ge=1, le=60),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    if len(site_names) > 20:
        return param_error('max 20 sites at once')

    if not site_names:
        return param_error('site list cannot be empty')

    catalog = catalog_svc.get_merged_site_catalog()

    valid_sites = []
    for site_name in site_names:
        site_info = catalog_svc.build_site_info(site_name, catalog)
        if not site_info or not site_info.get('test_url'):
            continue
        valid_sites.append((site_info['name'], site_info['test_url'], site_info.get('domains') or []))

    if not valid_sites:
        return param_error('no valid sites')

    tasks = [
        test_site_connectivity(url=test_url, timeout=timeout, follow_redirects=True)
        for _, test_url, _ in valid_sites
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results = []
    accessible_count = 0
    failed_count = 0
    total_response_time = 0
    response_time_count = 0

    for i, result in enumerate(results):
        site_name, test_url_used, all_domains = valid_sites[i]

        if isinstance(result, Exception):
            processed_results.append({
                'site_name': site_name,
                'domains': all_domains,
                'test_url': test_url_used,
                'accessible': False,
                'status': 'error',
                'error_message': str(result),
            })
            failed_count += 1
        else:
            processed_results.append({
                'site_name': site_name,
                'domains': all_domains,
                'test_url': result.url,
                'accessible': result.accessible,
                'status': result.status,
                'status_code': result.status_code,
                'response_time': result.response_time,
                'dns_resolved': result.dns_resolved,
                'ip_address': result.ip_address,
                'error_message': result.error_message,
            })
            if result.accessible:
                accessible_count += 1
            else:
                failed_count += 1
            if result.response_time:
                total_response_time += result.response_time
                response_time_count += 1

    avg_response_time = round(total_response_time / response_time_count, 2) if response_time_count > 0 else None
    total = len(processed_results)

    return success({
        'results': processed_results,
        'summary': {
            'total': total,
            'accessible': accessible_count,
            'failed': failed_count,
            'success_rate': round(accessible_count / total * 100, 2) if total > 0 else 0,
            'avg_response_time': avg_response_time,
        },
    })
