import asyncio
import logging
import mimetypes
from typing import Dict, List, Literal

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from services.site_login_status_service import (
    get_supported_sites as get_login_supported_sites,
    test_site_login_status,
)
from common.response import success, error, param_error
from routes.connectivity import test_site_connectivity
from core.site_config_manager import get_effective_site_catalog
from services.site_catalog_service import save_site_overrides
from utils.site_icons import build_site_icon_url, resolve_site_icon_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/sites', tags=['sites'])


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


def merge_site_names(catalog: dict) -> list[str]:
    """
    合并提取器注册表与站点配置中的站点名称，避免遗漏被禁用的站点
    """
    names: list[str] = []
    seen = set()

    for slug in catalog.keys():
        key = slug.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(slug)

    return names


def merge_site_catalogs(*catalogs: dict | None) -> dict:
    merged: dict = {}

    for catalog in catalogs:
        for raw_slug, raw_info in (catalog or {}).items():
            slug = str(raw_slug or '').strip().lower()
            if not slug:
                continue

            incoming = dict(raw_info or {})
            existing = merged.get(slug, {})
            merged_entry = dict(existing)

            if 'label' in incoming or 'label' not in merged_entry:
                merged_entry['label'] = incoming.get('label') or merged_entry.get('label') or raw_slug

            merged_entry['enabled'] = bool(incoming.get('enabled', merged_entry.get('enabled', True)))

            for key in ('test_url', 'icon_url'):
                value = incoming.get(key)
                if value:
                    merged_entry[key] = value

            for key in ('domains', 'aliases', 'features'):
                seen = set()
                values = []
                for item in list(merged_entry.get(key) or []) + list(incoming.get(key) or []):
                    normalized = str(item or '').strip().lower()
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    values.append(normalized)
                merged_entry[key] = values

            for key, value in incoming.items():
                if key in {'label', 'enabled', 'test_url', 'icon_url', 'domains', 'aliases', 'features'}:
                    continue
                if value is not None:
                    merged_entry[key] = value

            merged[slug] = merged_entry

    return merged


def get_merged_site_catalog() -> dict:
    return get_effective_site_catalog()


def build_site_info(site_name: str, catalog: dict) -> dict | None:
    """
    基于注册表与站点配置汇总站点信息，优先使用配置文件中的域名/测试URL
    """
    if not site_name:
        return None

    slug = site_name.lower()
    catalog_entry = catalog.get(slug, {})
    site_domains = catalog_entry.get("domains") or []

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
    icon_url = catalog_entry.get('icon_url')
    if not icon_url and resolve_site_icon_path(site_name):
        icon_url = build_site_icon_url(site_name)

    return {
        "name": site_name,
        "site_name": site_name,
        "label": catalog_entry.get('label', site_name),
        "domains": deduped_domains,
        "primary_domain": primary_domain,
        "test_url": test_url,
        "config_enabled": catalog_entry.get("enabled", True),
        "icon_url": icon_url,
    }


@router.get("")
def get_supported_sites():
    """
    获取插件支持的所有站点信息

    Returns:
        每个站点的详细信息，包括名称和对应的域名列表
    """
    catalog = get_merged_site_catalog()
    login_supported_sites = get_login_supported_sites()
    login_supported_sites_lower = {s.lower() for s in login_supported_sites}
    site_names = merge_site_names(catalog)

    # 构建每个站点的完整信息
    sites_info = []
    for site_name in site_names:
        info = build_site_info(site_name, catalog)
        if not info:
            continue
        info["supports_login_status"] = site_name.lower() in login_supported_sites_lower
        sites_info.append(info)

    return success({
        "sites": sites_info,
        "total": len(sites_info)
    })


@router.get("/catalog")
def get_sites_catalog():
    return success(get_effective_site_catalog())


@router.put("/catalog")
def update_sites_catalog(payload: dict = Body(...)):
    sites_payload = payload.get('sites') if isinstance(payload, dict) else None
    if not isinstance(sites_payload, dict):
        return param_error('sites 必须为对象')

    try:
        catalog = save_site_overrides(sites_payload)
        return success(catalog, msg="站点配置已更新")
    except ValueError as exc:
        return param_error(str(exc))
    except Exception:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to update site catalog")
        return error("保存站点配置失败")


@router.get('/{site_name}/icon', include_in_schema=False)
def get_site_icon(site_name: str):
    icon_path = resolve_site_icon_path(site_name)
    if icon_path is None:
        raise HTTPException(status_code=404, detail=f'No icon asset for site: {site_name}')
    media_type, _ = mimetypes.guess_type(icon_path.name)
    return FileResponse(path=icon_path, media_type=media_type or 'application/octet-stream')


@router.get("/{site_name}/test-connectivity")
async def test_site_connectivity_endpoint(site_name: str, timeout: int = Query(10, ge=1, le=60)):
    """
    测试指定站点的连通性

    Args:
        site_name: 站点名称（如: youtube, bilibili等）
        timeout: 超时时间（秒）

    Returns:
        连通性测试结果
    """
    catalog = get_merged_site_catalog()
    site_info = build_site_info(site_name, catalog)

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


@router.get("/{site_name}/login-status")
def get_site_login_status(site_name: str):
    catalog = get_merged_site_catalog()
    site_info = build_site_info(site_name, catalog)
    if not site_info:
        return param_error(f"不支持的站点: {site_name}")

    status = test_site_login_status(site_name)

    # For YouTube, also include OAuth status
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
            # task boundary -- prevent single failure from crashing request
            logger.warning('Failed to fetch YouTube OAuth status', exc_info=True)

    return success(status)


@router.post("/test-connectivity/batch")
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

    catalog = get_merged_site_catalog()

    # 过滤有效的站点
    valid_sites = []
    for site_name in site_names:
        site_info = build_site_info(site_name, catalog)
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


@router.get("/test-connectivity/all")
async def test_all_sites_connectivity(timeout: int = Query(10, ge=1, le=60)):
    """
    测试所有插件支持站点的连通性

    Args:
        timeout: 超时时间（秒）

    Returns:
        所有站点的测试结果
    """
    catalog = get_merged_site_catalog()
    site_names = merge_site_names(catalog)

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
        site_info = build_site_info(site_name, catalog)
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
                # task boundary -- prevent single failure from crashing request
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


# ── YouTube OAuth ─────────────────────────────────────────────────────────────

@router.post("/youtube/oauth/setup")
def setup_youtube_oauth():
    """
    Start YouTube TV OAuth flow.
    Returns verification URL and user code for user to complete authorization in browser.
    """
    try:
        from services.youtube_oauth_service import setup_oauth_via_daemon

        state = setup_oauth_via_daemon(timeout_seconds=60.0)
        return success({
            "status": state.status,
            "verification_url": state.verification_url,
            "user_code": state.user_code,
            "account": {
                "name": state.account.name if state.account else None,
                "email": state.account.email if state.account else None,
                "avatar": state.account.avatar if state.account else None,
            } if state.account or state.status == "authenticated" else None,
            "error": state.error,
        })
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        logger.exception("YouTube OAuth setup failed: %s", exc)
        return error(f"OAuth 启动失败: {exc}")


@router.get("/youtube/oauth/status")
def get_youtube_oauth_status():
    """
    Poll current YouTube OAuth status.
    Call this periodically after oauth/setup to detect when user completes authorization.
    """
    try:
        from services.youtube_oauth_service import poll_oauth_status_via_daemon

        state = poll_oauth_status_via_daemon(timeout_seconds=10.0)
        return success({
            "status": state.status,
            "verification_url": state.verification_url,
            "user_code": state.user_code,
            "account": {
                "name": state.account.name if state.account else None,
                "email": state.account.email if state.account else None,
                "avatar": state.account.avatar if state.account else None,
            } if state.account else None,
            "error": state.error,
        })
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        logger.exception("YouTube OAuth status check failed: %s", exc)
        return error(f"OAuth 状态查询失败: {exc}")


@router.delete("/youtube/oauth")
def revoke_youtube_oauth():
    """
    Revoke YouTube OAuth credentials and sign out.
    """
    try:
        from services.youtube_oauth_service import revoke_oauth_via_daemon

        ok = revoke_oauth_via_daemon(timeout_seconds=30.0)
        return success({"revoked": ok}, msg="已撤销 YouTube 授权" if ok else "撤销失败")
    except Exception as exc:
        # API boundary -- convert to HTTP error response
        logger.exception("YouTube OAuth revoke failed: %s", exc)
        return error(f"撤销授权失败: {exc}")
