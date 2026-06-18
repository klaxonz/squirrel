from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from infrastructure.http.response import error, param_error, success
from infrastructure.site_catalog.cookie_files import get_site_cookies_file_path, write_cookie_text_file
from infrastructure.site_catalog.login_status import SiteLoginStatusService
from infrastructure.site_catalog.routes.sites_dependencies import get_catalog_service, get_login_service
from infrastructure.site_catalog.service import SiteCatalogService

router = APIRouter()


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
