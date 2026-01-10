from fastapi import APIRouter, File, UploadFile, Query
import asyncio
import logging
from typing import Dict, List, Literal

from services.plugin_service import PluginService
from services.site_login_status_service import SiteLoginStatusService
from services.cookiecloud_service import CookieCloudSyncError, sync_cookiecloud_to_site_files
from plugins.loader import reload_plugins
from utils.redis_client import publish_plugin_reload_signal
from common.response import success, error, param_error
from core.extraction import get_extractor_registry
from routes.connectivity import test_site_connectivity
from core.cookie_config import (
    get_site_cookies_dir,
    get_site_cookies_file_path,
)
from utils.site_catalog import SiteCatalog

logger = logging.getLogger(__name__)


def normalize_cookie_domain(domain: str) -> str:
    if not domain:
        return ""
    d = str(domain).strip()
    if d.startswith("#HttpOnly_"):
        d = d[len("#HttpOnly_") :]
    return d.lstrip(".").lower()

def select_primary_domain(domains: list) -> str:
    """
    选择最合适的主域名
    优先级：1. www.开头的域名  2. 最短的域名  3. 第一个域名
    
    Args:
        domains: 域名列表
        
    Returns:
        选中的主域名
    """
    if not domains:
        return None
    
    # 优先选择 www. 开头的域名
    www_domains = [d for d in domains if d.startswith('www.')]
    if www_domains:
        return www_domains[0]
    
    # 如果没有 www. 开头的，选择最短的域名（通常是主域名）
    return min(domains, key=len)


def merge_site_names(registry, catalog: dict) -> list[str]:
    """
    合并提取器注册表与站点配置中的站点名称，避免遗漏被禁用的站点
    """
    names: list[str] = []
    seen = set()

    for site_name in registry.get_all_keys():
        key = site_name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(site_name)

    for slug in catalog.keys():
        key = slug.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(slug)

    return names


def build_site_info(site_name: str, registry, catalog: dict) -> dict | None:
    """
    基于注册表与站点配置汇总站点信息，优先使用配置文件中的域名/测试URL
    """
    if not site_name:
        return None

    slug = site_name.lower()
    catalog_entry = catalog.get(slug, {})
    domain_mapping = registry._domain_mapping

    site_domains = catalog_entry.get("domains") or [
        domain for domain, mapped_site in domain_mapping.items()
        if str(mapped_site).lower() == slug
    ]

    # 去重但保持顺序
    seen = set()
    deduped_domains = []
    for d in site_domains:
        if d in seen:
            continue
        seen.add(d)
        deduped_domains.append(d)

    primary_domain = select_primary_domain(deduped_domains)
    test_url = (
        catalog_entry.get("test_url")
        or (f"https://{primary_domain}" if primary_domain else None)
    )

    return {
        "name": site_name,
        "domains": deduped_domains,
        "primary_domain": primary_domain,
        "test_url": test_url,
        "config_enabled": catalog_entry.get("enabled", True),
    }


router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.post("/install")
def install_plugin(file: UploadFile = File(...)):
    filename = (file.filename or "plugin.zip").lower()
    if not filename.endswith(".zip"):
        return param_error("file must be a zip archive")
    ok, data_or_err = PluginService.install_from_upload(file)
    if ok:
        try:
            reload_plugins()
            publish_plugin_reload_signal()
            return success(data_or_err, msg="installed and loaded")
        except Exception as e:
            logger.error("failed to reload plugins after install: %s", e, exc_info=True)
            return success(data_or_err, msg="installed but reload failed, please reload manually")
    return error(data_or_err or "install failed")


@router.get("/")
def list_plugins():
    return success(PluginService.list_plugins())


@router.post("/{name}/enable")
def enable_plugin(name: str):
    ok = PluginService.set_enabled_by_name(name, True)
    if ok:
        return success(msg="enabled")
    return error("invalid plugin name or not found")


@router.post("/{name}/disable")
def disable_plugin(name: str):
    ok = PluginService.set_enabled_by_name(name, False)
    if ok:
        return success(msg="disabled")
    return error("invalid plugin name or not found")


@router.post("/{name}/uninstall")
def uninstall_plugin(name: str):
    ok = PluginService.uninstall_by_name(name)
    if ok:
        return success(msg="uninstalled")
    return error("invalid plugin name or not found, or not in plugins_ext")


@router.post("/reload")
def reload_all_plugins():
    reload_plugins()
    publish_plugin_reload_signal()
    return success(msg="reloaded")


@router.get("/sites")
def get_supported_sites():
    """
    获取插件支持的所有站点信息
    
    Returns:
        每个站点的详细信息，包括名称和对应的域名列表
    """
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    login_supported_sites = SiteLoginStatusService.get_supported_sites()
    login_supported_sites_lower = {s.lower() for s in login_supported_sites}
    site_names = merge_site_names(registry, catalog)
    
    # 构建每个站点的完整信息
    sites_info = []
    for site_name in site_names:
        info = build_site_info(site_name, registry, catalog)
        if not info:
            continue
        info["supports_login_status"] = site_name.lower() in login_supported_sites_lower
        sites_info.append(info)
    
    return success({
        "sites": sites_info,
        "total": len(sites_info)
    })


@router.get("/sites/{site_name}/test-connectivity")
async def test_site_connectivity_endpoint(site_name: str, timeout: int = Query(10, ge=1, le=60)):
    """
    测试指定站点的连通性
    
    Args:
        site_name: 站点名称（如: youtube, bilibili等）
        timeout: 超时时间（秒）
        
    Returns:
        连通性测试结果
    """
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    site_info = build_site_info(site_name, registry, catalog)

    if not site_info:
        return param_error(f"不支持的站点: {site_name}")
    
    site_domains = site_info.get("domains") or []
    test_url = site_info.get("test_url")

    if not site_domains and not test_url:
        return error(f"站点 {site_name} 没有关联的域名")
    if not test_url:
        return error(f"站点 {site_name} 未配置可用的测试URL")
    
    result = await test_site_connectivity(
        url=test_url,
        timeout=timeout,
        follow_redirects=True
    )
    
    return success({
        "site_name": site_name,
        "domains": site_domains,
        "test_url": result.url,
        "accessible": result.accessible,
        "status": result.status,
        "status_code": result.status_code,
        "response_time": result.response_time,
        "dns_resolved": result.dns_resolved,
        "ip_address": result.ip_address,
        "error_message": result.error_message
    })


@router.get("/sites/{site_name}/login-status")
def get_site_login_status(site_name: str):
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    site_info = build_site_info(site_name, registry, catalog)
    if not site_info:
        return param_error(f"不支持的站点: {site_name}")

    status = SiteLoginStatusService.test(site_name)
    return success(status)


@router.post("/sites/{site_name}/cookies")
async def upload_site_cookies(
    site_name: str,
    file: UploadFile = File(...),
    target: Literal["default", "http"] = Query("default")
):
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    site_info = build_site_info(site_name, registry, catalog)
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

    site_cookies_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    status = SiteLoginStatusService.test(site_name)
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


@router.post("/sites/cookies/import-all")
async def import_cookies_for_all_sites(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return param_error("文件为空")

    text = data.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    site_names = merge_site_names(registry, catalog)

    domain_to_sites: Dict[str, List[str]] = {}
    site_to_domains: Dict[str, List[str]] = {}
    for site_name in site_names:
        info = build_site_info(site_name, registry, catalog)
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
        path.write_text("\n".join(output) + "\n", encoding="utf-8")
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


@router.post("/sites/cookies/cookiecloud/sync")
def sync_cookies_from_cookiecloud(site_name: str | None = Query(None)):
    try:
        data = sync_cookiecloud_to_site_files(site_slug=site_name)
        return success(data, msg="CookieCloud 同步完成")
    except CookieCloudSyncError as exc:
        return error(str(exc))
    except Exception as exc:
        logger.exception("CookieCloud sync failed: %s", exc)
        return error(f"CookieCloud 同步失败: {exc}")


@router.post("/sites/test-connectivity/batch")
async def test_batch_sites_connectivity(
    site_names: List[str] = Query(..., description="站点名称列表"),
    timeout: int = Query(10, ge=1, le=60)
):
    """
    批量测试多个站点的连通性
    
    Args:
        site_names: 站点名称列表（最多20个）
        timeout: 超时时间（秒）
        
    Returns:
        批量测试结果
    """
    if len(site_names) > 20:
        return param_error("最多支持同时测试20个站点")
    
    if not site_names:
        return param_error("站点列表不能为空")
    
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    
    # 过滤有效的站点
    valid_sites = []
    for site_name in site_names:
        site_info = build_site_info(site_name, registry, catalog)
        if not site_info or not site_info.get("test_url"):
            continue
        valid_sites.append((site_info["name"], site_info["test_url"], site_info.get("domains") or []))
    
    if not valid_sites:
        return param_error("没有有效的站点")
    
    # 并发测试所有站点
    tasks = [
        test_site_connectivity(url=test_url, timeout=timeout, follow_redirects=True)
        for _, test_url, _ in valid_sites
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    processed_results = []
    accessible_count = 0
    failed_count = 0
    total_response_time = 0
    response_time_count = 0
    
    for i, result in enumerate(results):
        site_name, test_url_used, all_domains = valid_sites[i]
        
        if isinstance(result, Exception):
            processed_results.append({
                "site_name": site_name,
                "domains": all_domains,
                "test_url": test_url_used,
                "accessible": False,
                "status": "error",
                "error_message": str(result)
            })
            failed_count += 1
        else:
            processed_results.append({
                "site_name": site_name,
                "domains": all_domains,
                "test_url": result.url,
                "accessible": result.accessible,
                "status": result.status,
                "status_code": result.status_code,
                "response_time": result.response_time,
                "dns_resolved": result.dns_resolved,
                "ip_address": result.ip_address,
                "error_message": result.error_message
            })
            
            if result.accessible:
                accessible_count += 1
            else:
                failed_count += 1
            
            if result.response_time:
                total_response_time += result.response_time
                response_time_count += 1
    
    # 计算平均响应时间
    avg_response_time = None
    if response_time_count > 0:
        avg_response_time = round(total_response_time / response_time_count, 2)
    
    total = len(processed_results)
    
    return success({
        "results": processed_results,
        "summary": {
            "total": total,
            "accessible": accessible_count,
            "failed": failed_count,
            "success_rate": round(accessible_count / total * 100, 2) if total > 0 else 0,
            "avg_response_time": avg_response_time
        }
    })


@router.get("/sites/test-connectivity/all")
async def test_all_sites_connectivity(timeout: int = Query(10, ge=1, le=60)):
    """
    测试所有插件支持站点的连通性
    
    Args:
        timeout: 超时时间（秒）
        
    Returns:
        所有站点的测试结果
    """
    registry = get_extractor_registry()
    catalog = SiteCatalog.get_catalog() or {}
    site_names = merge_site_names(registry, catalog)
    
    if not site_names:
        return success({
            "results": [],
            "summary": {
                "total": 0,
                "accessible": 0,
                "failed": 0,
                "success_rate": 0,
                "avg_response_time": None
            }
        })
    
    test_sites = []
    for site_name in site_names:
        site_info = build_site_info(site_name, registry, catalog)
        if not site_info:
            continue
        test_url = site_info.get("test_url")
        if not test_url:
            continue
        test_sites.append((site_info["name"], test_url, site_info.get("domains") or []))
    
    MAX_CONCURRENT = 20
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def run_test(site_name: str, test_url: str, site_domains: list[str]):
        async with semaphore:
            try:
                result = await test_site_connectivity(url=test_url, timeout=timeout, follow_redirects=True)
                return site_name, test_url, site_domains, result, None
            except Exception as exc:
                return site_name, test_url, site_domains, None, exc

    tasks = [
        asyncio.create_task(run_test(site_name, test_url, site_domains))
        for site_name, test_url, site_domains in test_sites
    ]
    
    results = await asyncio.gather(*tasks)
    
    # 处理结果
    processed_results = []
    accessible_count = 0
    failed_count = 0
    total_response_time = 0
    response_time_count = 0
    
    for result in results:
        site_name, test_url_used, all_domains, success_result, error = result
        
        if error:
            processed_results.append({
                "site_name": site_name,
                "domains": all_domains,
                "test_url": test_url_used,
                "accessible": False,
                "status": "error",
                "error_message": str(error)
            })
            failed_count += 1
        else:
            processed_results.append({
                "site_name": site_name,
                "domains": all_domains,
                "test_url": success_result.url,
                "accessible": success_result.accessible,
                "status": success_result.status,
                "status_code": success_result.status_code,
                "response_time": success_result.response_time,
                "dns_resolved": success_result.dns_resolved,
                "ip_address": success_result.ip_address,
                "error_message": success_result.error_message
            })
            
            if success_result.accessible:
                accessible_count += 1
            else:
                failed_count += 1
            
            if success_result.response_time:
                total_response_time += success_result.response_time
                response_time_count += 1
    
    avg_response_time = None
    if response_time_count > 0:
        avg_response_time = round(total_response_time / response_time_count, 2)
    
    total = len(processed_results)
    
    return success({
        "results": processed_results,
        "summary": {
            "total": total,
            "accessible": accessible_count,
            "failed": failed_count,
            "success_rate": round(accessible_count / total * 100, 2) if total > 0 else 0,
            "avg_response_time": avg_response_time
        }
    })


