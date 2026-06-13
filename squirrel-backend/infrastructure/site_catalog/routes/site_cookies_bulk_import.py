from fastapi import APIRouter, Depends, File, UploadFile

from shared_kernel.application.response import param_error, success
from infrastructure.site_catalog.cookie_files import get_site_cookies_dir, get_site_cookies_file_path, write_cookie_text_file
from infrastructure.site_catalog.routes.site_cookies_dependencies import get_catalog_service
from infrastructure.site_catalog.service import SiteCatalogService

router = APIRouter()


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
