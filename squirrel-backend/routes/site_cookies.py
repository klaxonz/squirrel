import logging
from typing import Dict, List, Literal

from fastapi import APIRouter, File, Query, UploadFile

from common.response import success, error, param_error
from core.cookie_config import get_site_cookies_dir, get_site_cookies_file_path, write_cookie_text_file
from services.cookiecloud_service import CookieCloudSyncError, sync_cookiecloud_to_site_files
from services.site_login_status_service import test_site_login_status
from services.site_catalog_service import build_site_info, get_merged_site_catalog, merge_site_names, normalize_cookie_domain

router = APIRouter(prefix='/api/site-cookies', tags=['site-cookies'])
logger = logging.getLogger(__name__)


@router.post('/{site_name}')
async def upload_site_cookies(
    site_name: str,
    file: UploadFile = File(...),
    target: Literal["default", "http"] = Query("default")
):
    catalog = get_merged_site_catalog()
    site_info = build_site_info(site_name, catalog)
    if not site_info:
        return param_error(f"不支持的站点: {site_name}")

    data = await file.read()
    if not data:
        return param_error("文件为空")

    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    site_domains = [d.strip().lstrip(".").lower() for d in (site_info.get("domains") or []) if d]
    if not site_domains:
        return error(f"站点 {site_name} 没有关联的域名，无法从 cookies 文件中切分")

    header_lines: List[str] = []
    body_lines: List[str] = []
    for line in lines:
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            header_lines.append(line)
            continue
        parts = line.split("\t")
        if not parts:
            continue
        domain = normalize_cookie_domain(parts[0])
        if any(domain == d or domain.endswith("." + d) for d in site_domains):
            body_lines.append(line)

    if not body_lines:
        return error("在该文件中未找到与当前站点域名匹配的 Cookie 条目")

    site_cookies_path = get_site_cookies_file_path(site_name)
    site_cookies_path.parent.mkdir(parents=True, exist_ok=True)

    output_lines: List[str] = []
    output_lines.extend(l for l in header_lines if l)
    if not output_lines or not output_lines[0].startswith("# Netscape HTTP Cookie File"):
        output_lines.insert(0, "# Netscape HTTP Cookie File")
    output_lines.extend(body_lines)

    write_cookie_text_file(site_cookies_path, '\n'.join(output_lines) + '\n')

    status = test_site_login_status(site_name)
    return success(
        {
            "site_name": site_name,
            "target": target,
            "bytes": len(data),
            "site_cookies_bytes": site_cookies_path.stat().st_size,
            "login_status": status,
        },
        msg="Cookies 已更新"
    )


@router.post("/import-all")
async def import_cookies_for_all_sites(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return param_error("文件为空")

    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    catalog = get_merged_site_catalog()
    site_names = merge_site_names(catalog)

    domain_to_sites: Dict[str, List[str]] = {}
    site_to_domains: Dict[str, List[str]] = {}
    for site_name in site_names:
        info = build_site_info(site_name, catalog)
        if not info:
            continue
        domains = [d.strip().lstrip(".").lower() for d in (info.get("domains") or []) if d]
        if not domains:
            continue
        site_to_domains[site_name] = domains
        for d in domains:
            domain_to_sites.setdefault(d, []).append(site_name)

    site_lines: Dict[str, List[str]] = {name: [] for name in site_to_domains.keys()}
    header_lines: List[str] = []

    for line in lines:
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            header_lines.append(line)
            continue
        parts = line.split("\t")
        if not parts:
            continue
        raw_domain = normalize_cookie_domain(parts[0])
        matched_sites: List[str] = []
        for d, names in domain_to_sites.items():
            if raw_domain == d or raw_domain.endswith("." + d):
                matched_sites.extend(names)
        if not matched_sites:
            continue
        for site in matched_sites:
            site_lines.setdefault(site, []).append(line)

    get_site_cookies_dir().mkdir(parents=True, exist_ok=True)

    result_summary: Dict[str, Dict[str, int]] = {}
    for site_name, body in site_lines.items():
        if not body:
            continue
        path = get_site_cookies_file_path(site_name)
        output: List[str] = []
        output.extend(l for l in header_lines if l)
        if not output or not output[0].startswith("# Netscape HTTP Cookie File"):
            output.insert(0, "# Netscape HTTP Cookie File")
        output.extend(body)
        write_cookie_text_file(path, '\n'.join(output) + '\n')
        result_summary[site_name] = {"cookies": len(body)}

    total_lines = len(lines)
    matched_lines = sum(info["cookies"] for info in result_summary.values())

    return success(
        {
            "file_name": file.filename,
            "total_lines": total_lines,
            "matched_lines": matched_lines,
            "sites": result_summary,
        },
        msg="Cookies 已按站点拆分导入"
    )


@router.post("/cookiecloud/sync")
def sync_cookies_from_cookiecloud(site_name: str | None = Query(None)):
    try:
        data = sync_cookiecloud_to_site_files(site_slug=site_name)
        return success(data, msg="CookieCloud 同步完成")
    except CookieCloudSyncError as exc:
        return error(str(exc))
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        logger.exception("CookieCloud sync failed: %s", exc)
        return error(f"CookieCloud 同步失败: {exc}")
