import logging
import json
from datetime import datetime

from fastapi import APIRouter, Query, Depends, Request
import common.response as response
from models.user import User
from schemas.subscription.request.subscription import SubscribeRequest, UnsubscribeRequest, ToggleStatusRequest, ImportSubscriptionsRequest
from services import (
    subscription_service,
    subscription_sync_center_service,
    subscription_sync_history_service,
    subscription_sync_trend_service,
    video_extraction_center_service,
)
from typing import List
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain
from utils.jwt_helper import get_current_user

router = APIRouter(tags=['订阅接口'])
logger = logging.getLogger(__name__)
SYNC_CENTER_ALLOWED_STATUS = {'failed', 'running', 'queued', 'scheduled', 'recent'}
EXTRACTION_CENTER_ALLOWED_STATUS = {'failed', 'running', 'queued', 'recent'}
SYNC_HISTORY_ALLOWED_STATUS = {'created', 'queued', 'running', 'success', 'failed', 'deferred', 'timeout', 'recent', 'feed_recent'}


def _normalize_site_name(site: str) -> str:
    return str(site or '').strip().lower()


def _get_supported_site_set(supported_sites: List[str]) -> set[str]:
    return {_normalize_site_name(site) for site in supported_sites if _normalize_site_name(site)}


def _get_enabled_import_sites(supported_sites: List[str]) -> List[str]:
    supported_site_set = _get_supported_site_set(supported_sites)
    return [site for site in supported_site_set if SiteCatalog.is_site_enabled(site=site)]


@router.post("/api/subscription/subscribe")
def subscribe_content(req: SubscribeRequest, current_user: User = Depends(get_current_user)):
    domain = extract_top_level_domain(req.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法订阅")

    subscription_service.create_subscribe_message(req.url, current_user.id)
    return response.success()


@router.post("/api/subscription/unsubscribe")
def unsubscribe_content(req: UnsubscribeRequest, current_user: User = Depends(get_current_user)):
    subscription_service.unsubscribe_by_id(current_user.id, req.subscription_id)
    return response.success()


@router.get("/api/subscription/status")
def get_subscription_status(
        url: str = Query(None),
        current_user: User = Depends(get_current_user)
):
    is_subscribed = subscription_service.check_subscription_status(current_user.id, url)
    return response.success({
        "is_subscribed": is_subscribed
    })


@router.get("/api/subscription/detail/{subscription_id}")
def get_subscription_detail(subscription_id: int, current_user: User = Depends(get_current_user)):
    """获取订阅（频道）详情，附带当前用户的 is_nsfw 状态和统计字段"""
    sub = subscription_service.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found("订阅不存在")

    is_nsfw = subscription_service.get_user_subscription_nsfw(current_user.id, subscription_id)
    data = sub.model_dump() if hasattr(sub, 'model_dump') else dict(sub)
    data["is_nsfw"] = bool(is_nsfw) if is_nsfw is not None else False
    return response.success(data)


@router.get("/api/subscription/list")
def list_subscriptions(
        query: str = Query(None, description="搜索关键字"),
        type: str = Query(None, description="内容类型"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    domains: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains = resolved if resolved else None

    subscriptions, total = subscription_service.list_subscriptions(
        current_user.id, query, type, nsfw, page, page_size, domains
    )
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.get('/api/subscription/options')
def get_subscription_options(current_user: User = Depends(get_current_user)):
    return response.success({
        'data': subscription_service.list_subscription_options(current_user.id)
    })


@router.get('/api/subscription/sync-center/overview')
def get_sync_center_overview(current_user: User = Depends(get_current_user)):
    overview = subscription_sync_center_service.get_sync_center_overview(current_user.id)
    return response.success(overview)


@router.get('/api/subscription/sync-center/items')
def get_sync_center_items(
        status: str = Query(None, description='同步状态筛选'),
        site: str = Query(None, description='站点筛选'),
        query: str = Query(None, description='订阅搜索关键字'),
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, alias='pageSize', description='每页数量'),
        current_user: User = Depends(get_current_user)
):
    normalized_status = str(status or '').strip().lower() or None
    if normalized_status and normalized_status not in SYNC_CENTER_ALLOWED_STATUS:
        return response.param_error(f'不支持的状态筛选: {status}')

    result = subscription_sync_center_service.list_sync_center_items(
        current_user.id,
        normalized_status,
        site,
        query,
        page,
        page_size,
    )
    return response.success({
        'total': result.total,
        'page': result.page,
        'pageSize': result.page_size,
        'data': result.data,
    })


@router.get('/api/subscription/sync-center/feed-snapshot')
def get_sync_center_feed_snapshot(
        site: str = Query(None, description='站点筛选'),
        query: str = Query(None, description='订阅搜索关键字'),
        date_from: str = Query(None, alias='dateFrom', description='开始时间'),
        date_to: str = Query(None, alias='dateTo', description='结束时间'),
        current_user: User = Depends(get_current_user)
):
    result = subscription_sync_center_service.get_feed_dashboard_snapshot(
        user_id=current_user.id,
        site=site,
        query=query,
        date_from=date_from,
        date_to=date_to,
    )
    return response.success(result)


@router.get('/api/subscription/extraction-center/overview')
def get_extraction_center_overview(current_user: User = Depends(get_current_user)):
    overview = video_extraction_center_service.get_extraction_center_overview(current_user.id)
    return response.success(overview)


@router.get('/api/subscription/extraction-center/items')
def get_extraction_center_items(
        status: str = Query(None, description='提取状态筛选'),
        site: str = Query(None, description='站点筛选'),
        query: str = Query(None, description='订阅搜索关键字'),
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, alias='pageSize', description='每页数量'),
        current_user: User = Depends(get_current_user)
):
    normalized_status = str(status or '').strip().lower() or None
    if normalized_status and normalized_status not in EXTRACTION_CENTER_ALLOWED_STATUS:
        return response.param_error(f'不支持的提取状态筛选: {status}')

    result = video_extraction_center_service.list_extraction_center_items(
        current_user.id,
        normalized_status,
        site,
        query,
        page,
        page_size,
    )
    return response.success({
        'total': result.total,
        'page': result.page,
        'pageSize': result.page_size,
        'data': result.data,
    })


@router.post("/api/subscription/{subscription_id}/refresh")
def refresh_subscription(
    subscription_id: int,
    request: Request,
    mode: str = Query('incremental', description='同步模式: incremental|full', pattern=r'^(incremental|full)$'),
    current_user: User = Depends(get_current_user)
):
    """
    手动刷新订阅
    职责：验证权限后调用调度器，具体更新逻辑由调度器和编排器处理
    """
    subscription, status = subscription_service.verify_subscription_access(current_user.id, subscription_id)
    if status == "not_found":
        return response.not_found("订阅不存在")
    if status == "forbidden":
        return response.forbidden("无权操作该订阅")

    domain = extract_top_level_domain(subscription.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法刷新订阅")

    from services.subscription_update import scheduler, UpdateTrigger, UpdateMode

    trace_id = getattr(request.state, 'trace_id', None)

    result = scheduler.schedule_one(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == 'full' else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id
    )

    if result.status == 'failed':
        return response.server_error("刷新请求失败")

    return response.success({
        "mode": mode,
        "status": result.status,
        "inProgress": result.status == 'in_progress',
        "subscriptionId": subscription_id,
        "requestId": result.request_id,
        "queuedAt": datetime.utcnow().isoformat() if result.status == 'queued' else None
    })


@router.get('/api/subscription/sync-center/runs')
def get_sync_center_runs(
        status: str = Query(None, description='运行状态筛选'),
        site: str = Query(None, description='站点筛选'),
        subscription_id: int = Query(None, alias='subscriptionId', description='频道筛选'),
        mode: str = Query(None, description='同步模式筛选'),
        trigger: str = Query(None, description='触发方式筛选'),
        date_from: str = Query(None, alias='dateFrom', description='开始时间'),
        date_to: str = Query(None, alias='dateTo', description='结束时间'),
        page: int = Query(1, ge=1, description='页码'),
        page_size: int = Query(20, ge=1, le=100, alias='pageSize', description='每页数量'),
        current_user: User = Depends(get_current_user)
):
    normalized_status = str(status or '').strip().lower() or None
    if normalized_status and normalized_status not in SYNC_HISTORY_ALLOWED_STATUS:
        return response.param_error(f'不支持的运行状态筛选: {status}')

    result = subscription_sync_history_service.list_runs(
        current_user.id,
        status=normalized_status,
        site=site,
        subscription_id=subscription_id,
        mode=mode,
        trigger=trigger,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return response.success(result)
@router.get('/api/subscription/sync-center/runs/{run_id}')
def get_sync_center_run_detail(run_id: str, current_user: User = Depends(get_current_user)):
    result = subscription_sync_history_service.get_run_detail(run_id, current_user.id)
    if not result:
        return response.not_found('运行实例不存在')
    return response.success(result)


@router.get('/api/subscription/sync-center/runs/{run_id}/events')
def get_sync_center_run_events(run_id: str, current_user: User = Depends(get_current_user)):
    detail = subscription_sync_history_service.get_run_detail(run_id, current_user.id)
    if not detail:
        return response.not_found('运行实例不存在')
    return response.success(subscription_sync_history_service.list_run_events(run_id, current_user.id))


@router.get('/api/subscription/sync-center/trends')
def get_sync_center_trends(
        range_key: str = Query('24h', alias='range', description='时间范围: 24h|7d|30d'),
        site: str = Query(None, description='站点筛选'),
        mode: str = Query(None, description='同步模式筛选'),
        trigger: str = Query(None, description='触发方式筛选'),
        current_user: User = Depends(get_current_user)
):
    result = subscription_sync_trend_service.get_trends(
        user_id=current_user.id,
        range_key=range_key,
        site=site,
        mode=mode,
        trigger=trigger,
    )
    return response.success(result)


@router.get('/api/subscription/sync-center/recovery-summary')
def get_sync_center_recovery_summary(current_user: User = Depends(get_current_user)):
    return response.success(subscription_sync_history_service.get_recovery_summary(current_user.id))


@router.post("/api/subscription/toggle-nsfw")
def toggle_nsfw(
        req: ToggleStatusRequest,
        current_user: User = Depends(get_current_user)
):
    success = subscription_service.toggle_nsfw_status(
        current_user.id,
        req.subscription_id,
        req.is_enable
    )
    return response.success({"success": success})


@router.get("/api/subscription/import/sites")
def get_supported_sites(current_user: User = Depends(get_current_user)):
    """
    获取支持导入的站点列表
    
    Returns:
        支持的站点列表
    """
    supported_sites = subscription_service.get_runtime_supported_sites('import_subscriptions')
    enabled_sites = _get_enabled_import_sites(supported_sites)
    
    return response.success({
        "sites": enabled_sites
    })


@router.get("/api/subscription/import/{site}/preview")
def preview_subscriptions(
    site: str,
    cursor: str | None = Query(None, description='分页游标 JSON'),
    limit: int = Query(50, ge=1, le=200, description='每次预览加载数量'),
    current_user: User = Depends(get_current_user)
):
    """
    预览用户在指定站点的订阅列表（不实际导入）
    
    Args:
        site: 站点名称
        
    Returns:
        预览结果
    """
    try:
        supported_sites = subscription_service.get_runtime_supported_sites('import_subscriptions')
        supported_site_set = _get_supported_site_set(supported_sites)
        normalized_site = _normalize_site_name(site)
        enabled_sites = _get_enabled_import_sites(supported_sites)

        if normalized_site not in supported_site_set:
            return response.param_error(f"不支持的站点: {site}，支持的站点: {', '.join(supported_sites)}")
        if normalized_site not in enabled_sites:
            return response.param_error(f"站点已禁用，无法预览订阅: {site}")

        cursor_payload = None
        if cursor:
            try:
                parsed_cursor = json.loads(cursor)
            except json.JSONDecodeError as exc:
                raise ValueError(f'无效的预览游标: {exc.msg}') from exc
            if not isinstance(parsed_cursor, dict):
                raise ValueError('无效的预览游标: 必须为 JSON object')
            cursor_payload = parsed_cursor

        logger.info(f"User {current_user.id} previewing subscriptions from {normalized_site}")

        result = subscription_service.preview_user_subscriptions(
            normalized_site,
            current_user.id,
            cursor_payload=cursor_payload,
            limit=limit,
        )
        
        return response.success(result)
        
    except ValueError as e:
        logger.error(f"Invalid request for site {site}: {e}")
        return response.param_error(str(e))
    except Exception as e:
        logger.exception(f"Failed to preview subscriptions from {site}: {e}")
        return response.server_error(f"预览失败: {str(e)}")


@router.post("/api/subscription/import/{site}")
def import_subscriptions(
    site: str,
    req: ImportSubscriptionsRequest | None = None,
    current_user: User = Depends(get_current_user)
):
    """
    从指定站点导入用户的所有订阅
    
    Args:
        site: 站点名称（动态支持所有已注册的站点）
        
    Returns:
        导入结果统计
    """
    try:
        supported_sites = subscription_service.get_runtime_supported_sites('import_subscriptions')
        supported_site_set = _get_supported_site_set(supported_sites)
        normalized_site = _normalize_site_name(site)
        enabled_sites = _get_enabled_import_sites(supported_sites)

        if normalized_site not in supported_site_set:
            return response.param_error(f"不支持的站点: {site}，支持的站点: {', '.join(supported_sites)}")
        if normalized_site not in enabled_sites:
            return response.param_error(f"站点已禁用，无法导入订阅: {site}")

        logger.info(f"User {current_user.id} importing subscriptions from {normalized_site}")

        selected_urls = req.subscription_urls if req else None
        result = subscription_service.import_user_subscriptions(normalized_site, current_user.id, selected_urls=selected_urls)

        return response.success({
            "site": normalized_site,
            "total": result['total'],
            "found": result["found"],
            "selected": result["selected"],
            "skipped": result["skipped"]
        })
        
    except ValueError as e:
        logger.error(f"Invalid request for site {site}: {e}")
        return response.param_error(str(e))
    except Exception as e:
        logger.exception(f"Failed to import subscriptions from {site}: {e}")
        return response.server_error(f"导入失败: {str(e)}")
