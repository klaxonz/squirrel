import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from common.response import error, param_error, success
from core.cookie_config import get_site_cookies_dir, get_site_cookies_file_path, write_cookie_text_file
from services.cookiecloud_service import CookieCloudSyncError, sync_cookiecloud_to_site_files
from services.site_catalog_service import SiteCatalogService
from services.site_login_status_service import SiteLoginStatusService

router = APIRouter(prefix='/api/site-cookies', tags=['site-cookies'])
logger = logging.getLogger(__name__)


def get_catalog_service():
    return SiteCatalogService()


def get_login_service():
    return SiteLoginStatusService()


@router.post('/{site_name}')
async def upload_site_cookies(
    site_name: str,
    file: UploadFile = File(...),
    target: Literal['default', 'http'] = Query('default'),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
    login_svc: SiteLoginStatusService = Depends(get_login_service),
):
    catalog = catalog_svc.get_merged_site_catalog()
    site_info = catalog_svc.build_site_info(site_name, catalog)
    if not site_info:
        return param_error(f'unsupported site: {site_name}')

    data = await file.read()
    if not data:
        return param_error('file is empty')

    text = data.decode('utf-8', errors='ignore')
    lines = text.splitlines()

    site_domains = [d.strip().lstrip('.').lower() for d in (site_info.get('domains') or []) if d]
    if not site_domains:
        return error(f'site {site_name} has no associated domains')

    header_lines: list[str] = []
    body_lines: list[str] = []
    for line in lines:
        if not line:
            continue
        if line.startswith('#') and not line.startswith('#HttpOnly_'):
            header_lines.append(line)
            continue
        parts = line.split('\t')
        if not parts:
            continue
        domain = catalog_svc.normalize_cookie_domain(parts[0])
        if any(domain == d or domain.endswith('.' + d) for d in site_domains):
            body_lines.append(line)

    if not body_lines:
        return error('no cookie entries matched the site domain')

    site_cookies_path = get_site_cookies_file_path(site_name)
    site_cookies_path.parent.mkdir(parents=True, exist_ok=True)

    output_lines: list[str] = []
    output_lines.extend(line for line in header_lines if line)
    if not output_lines or not output_lines[0].startswith('# Netscape HTTP Cookie File'):
        output_lines.insert(0, '# Netscape HTTP Cookie File')
    output_lines.extend(body_lines)

    write_cookie_text_file(site_cookies_path, '\n'.join(output_lines) + '\n')

    status = login_svc.test_site_login_status(site_name)
    return success(
        {
            'site_name': site_name,
            'target': target,
            'bytes': len(data),
            'site_cookies_bytes': site_cookies_path.stat().st_size,
            'login_status': status,
        },
        msg='cookies updated',
    )


@router.post('/import-all')
async def import_cookies_for_all_sites(
    file: UploadFile = File(...),
    catalog_svc: SiteCatalogService = Depends(get_catalog_service),
):
    data = await file.read()
    if not data:
        return param_error('file is empty')

    text = data.decode('utf-8', errors='ignore')
    lines = text.splitlines()

    catalog = catalog_svc.get_merged_site_catalog()
    site_names = catalog_svc.merge_site_names(catalog)

    domain_to_sites: dict[str, list[str]] = {}
    site_to_domains: dict[str, list[str]] = {}
    for site_name in site_names:
        site_info = catalog_svc.build_site_info(site_name, catalog)
        if not site_info:
            continue
        domains = [d.strip().lstrip('.').lower() for d in (site_info.get('domains') or []) if d]
        if not domains:
            continue
        site_to_domains[site_name] = domains
        for d in domains:
            domain_to_sites.setdefault(d, []).append(site_name)

    site_lines: dict[str, list[str]] = {name: [] for name in site_to_domains}
    header_lines: list[str] = []

    for line in lines:
        if not line:
            continue
        if line.startswith('#') and not line.startswith('#HttpOnly_'):
            header_lines.append(line)
            continue
        parts = line.split('\t')
        if not parts:
            continue
        raw_domain = catalog_svc.normalize_cookie_domain(parts[0])
        matched_sites: list[str] = []
        for d, names in domain_to_sites.items():
            if raw_domain == d or raw_domain.endswith('.' + d):
                matched_sites.extend(names)
        if not matched_sites:
            continue
        for site in matched_sites:
            site_lines.setdefault(site, []).append(line)

    get_site_cookies_dir().mkdir(parents=True, exist_ok=True)

    result_summary: dict[str, dict[str, int]] = {}
    for site_name, body in site_lines.items():
        if not body:
            continue
        path = get_site_cookies_file_path(site_name)
        output: list[str] = []
        output.extend(line for line in header_lines if line)
        if not output or not output[0].startswith('# Netscape HTTP Cookie File'):
            output.insert(0, '# Netscape HTTP Cookie File')
        output.extend(body)
        write_cookie_text_file(path, '\n'.join(output) + '\n')
        result_summary[site_name] = {'cookies': len(body)}

    total_lines = len(lines)
    matched_lines = sum(entry['cookies'] for entry in result_summary.values())

    return success(
        {
            'file_name': file.filename,
            'total_lines': total_lines,
            'matched_lines': matched_lines,
            'sites': result_summary,
        },
        msg='cookies split by site',
    )


@router.post('/cookiecloud/sync')
def sync_cookies_from_cookiecloud(site_name: str | None = Query(None)):
    try:
        data = sync_cookiecloud_to_site_files(site_slug=site_name)
        return success(data, msg='CookieCloud sync completed')
    except CookieCloudSyncError as exc:
        return error(str(exc))
    except Exception as exc:
        logger.exception('CookieCloud sync failed: %s', exc)
        return error(f'CookieCloud sync failed: {exc}')
