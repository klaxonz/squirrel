import asyncio
import logging
import mimetypes

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from common.response import error, param_error, success
from routes.connectivity import test_site_connectivity
from services.site_catalog_service import SiteCatalogService
from services.site_login_status_service import SiteLoginStatusService
from utils.site_icons import resolve_site_icon_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/sites', tags=['sites'])


def get_catalog_service():
    return SiteCatalogService()


def get_login_service():
    return SiteLoginStatusService()


@router.get('')
def get_supported_sites(
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
    login_svc: SiteLoginStatusService = Depends(get_login_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    login_supported_sites = login_svc.get_supported_sites()
    login_supported_sites_lower = {s.lower() for s in login_supported_sites}
    site_names = catalog_svc.merge_site_names(catalog)

    sites_info = []
    for site_name in site_names:
        site_cfg = catalog_svc.build_site_info(site_name, catalog)
        if not site_cfg:
            continue
        site_cfg['supports_login_status'] = site_name.lower() in login_supported_sites_lower
        sites_info.append(site_cfg)

    return success({
        'sites': sites_info,
        'total': len(sites_info),
    })


@router.get('/catalog')
def get_sites_catalog(
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    return success(catalog_svc.get_merged_site_catalog())


@router.put('/catalog')
def update_sites_catalog(
    payload: dict = Body(...),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    sites_payload = payload.get('sites') if isinstance(payload, dict) else None
    if not isinstance(sites_payload, dict):
        return param_error('sites must be a dict')

    try:
        catalog = catalog_svc.save_site_overrides(sites_payload)
        return success(catalog, msg='site config updated')
    except ValueError as exc:
        return param_error(str(exc))
    except Exception:
        logger.exception('Failed to update site catalog')
        return error('failed to save site config')


@router.get('/{site_name}/icon', include_in_schema=False)
def get_site_icon(site_name: str):
    icon_path = resolve_site_icon_path(site_name)
    if icon_path is None:
        raise HTTPException(status_code=404, detail=f'No icon asset for site: {site_name}')
    media_type, _ = mimetypes.guess_type(icon_path.name)
    return FileResponse(path=icon_path, media_type=media_type or 'application/octet-stream')


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


@router.get('/{site_name}/login-status')
def get_site_login_status(
    site_name: str,
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
    login_svc: SiteLoginStatusService = Depends(get_login_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    site_info = catalog_svc.build_site_info(site_name, catalog)
    if not site_info:
        return param_error(f'Unsupported site: {site_name}')

    status = login_svc.test_site_login_status(site_name)

    if site_name.lower() == 'youtube':
        try:
            from services.youtube_oauth_service import get_oauth_state
            oauth_state = get_oauth_state()
            status['oauth_status'] = oauth_state.status
            status['oauth_account'] = {
                'name': oauth_state.account.name if oauth_state.account else None,
                'email': oauth_state.account.email if oauth_state.account else None,
                'avatar': oauth_state.account.avatar if oauth_state.account else None,
            } if oauth_state.account else None
        except Exception:
            logger.warning('Failed to fetch YouTube OAuth status', exc_info=True)

    return success(status)


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

    MAX_CONCURRENT = 20
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

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


# YouTube OAuth

@router.post('/youtube/oauth/setup')
def setup_youtube_oauth():
    try:
        from services.youtube_oauth_service import setup_oauth_via_daemon
        state = setup_oauth_via_daemon(timeout_seconds=60.0)
        return success({
            'status': state.status,
            'verification_url': state.verification_url,
            'user_code': state.user_code,
            'account': {
                'name': state.account.name if state.account else None,
                'email': state.account.email if state.account else None,
                'avatar': state.account.avatar if state.account else None,
            } if state.account or state.status == 'authenticated' else None,
            'error': state.error,
        })
    except Exception as exc:
        logger.exception('YouTube OAuth setup failed: %s', exc)
        return error(f'OAuth setup failed: {exc}')


@router.get('/youtube/oauth/status')
def get_youtube_oauth_status():
    try:
        from services.youtube_oauth_service import poll_oauth_status_via_daemon
        state = poll_oauth_status_via_daemon(timeout_seconds=10.0)
        return success({
            'status': state.status,
            'verification_url': state.verification_url,
            'user_code': state.user_code,
            'account': {
                'name': state.account.name if state.account else None,
                'email': state.account.email if state.account else None,
                'avatar': state.account.avatar if state.account else None,
            } if state.account else None,
            'error': state.error,
        })
    except Exception as exc:
        logger.exception('YouTube OAuth status check failed: %s', exc)
        return error(f'OAuth status query failed: {exc}')


@router.delete('/youtube/oauth')
def revoke_youtube_oauth():
    try:
        from services.youtube_oauth_service import revoke_oauth_via_daemon
        ok = revoke_oauth_via_daemon(timeout_seconds=30.0)
        return success({'revoked': ok}, msg='YouTube authorization revoked' if ok else 'Revocation failed')
    except Exception as exc:
        logger.exception('YouTube OAuth revoke failed: %s', exc)
        return error(f'Authorization revocation failed: {exc}')
