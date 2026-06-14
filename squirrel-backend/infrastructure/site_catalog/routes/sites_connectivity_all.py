import asyncio

from fastapi import APIRouter, Depends, Query

from infrastructure.site_catalog.connectivity import test_site_connectivity
from infrastructure.site_catalog.routes.sites_dependencies import get_catalog_service
from infrastructure.site_catalog.service import SiteCatalogService
from shared_kernel.application.response import success

router = APIRouter()


@router.get('/test-connectivity/all')
async def test_all_sites_connectivity(
    timeout: int = Query(10, ge=1, le=60),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    site_names = catalog_svc.merge_site_names(catalog)

    if not site_names:
        return success({
            'results': [],
            'summary': {'total': 0, 'accessible': 0, 'failed': 0, 'success_rate': 0, 'avg_response_time': None},
        })

    test_sites = []
    for site_name in site_names:
        site_info = catalog_svc.build_site_info(site_name, catalog)
        if not site_info:
            continue
        test_url = site_info.get('test_url')
        if not test_url:
            continue
        test_sites.append((site_info['name'], test_url, site_info.get('domains') or []))

    max_concurrent = 20
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_test(site_name, test_url, site_domains):
        async with semaphore:
            try:
                connectivity_result = await test_site_connectivity(url=test_url, timeout=timeout, follow_redirects=True)
                return site_name, test_url, site_domains, connectivity_result, None
            except Exception as exc:
                return site_name, test_url, site_domains, None, exc

    tasks = [
        asyncio.create_task(run_test(site_name, test_url, site_domains))
        for site_name, test_url, site_domains in test_sites
    ]

    results = await asyncio.gather(*tasks)

    processed_results = []
    accessible_count = 0
    failed_count = 0
    total_response_time = 0
    response_time_count = 0

    for result in results:
        site_name, test_url_used, all_domains, success_result, error_result = result

        if error_result:
            processed_results.append({
                'site_name': site_name,
                'domains': all_domains,
                'test_url': test_url_used,
                'accessible': False,
                'status': 'error',
                'error_message': str(error_result),
            })
            failed_count += 1
        else:
            processed_results.append({
                'site_name': site_name,
                'domains': all_domains,
                'test_url': success_result.url,
                'accessible': success_result.accessible,
                'status': success_result.status,
                'status_code': success_result.status_code,
                'response_time': success_result.response_time,
                'dns_resolved': success_result.dns_resolved,
                'ip_address': success_result.ip_address,
                'error_message': success_result.error_message,
            })
            if success_result.accessible:
                accessible_count += 1
            else:
                failed_count += 1
            if success_result.response_time:
                total_response_time += success_result.response_time
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
