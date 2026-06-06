import logging
import json
from datetime import datetime

from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import StreamingResponse
import common.response as response
from models.user import User
from schemas.subscription.request.subscription import SubscribeRequest, UnsubscribeRequest, ToggleStatusRequest, ImportSubscriptionsRequest
from services import (
    subscription_service,
    subscription_sync_history_service,
    sync_center_stream_service,
)
from typing import List
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain
from utils.jwt_helper import get_current_user

router = APIRouter(prefix='/api/subscription', tags=['订阅接口'])
logger = logging.getLogger(__name__)
SYNC_HISTORY_ALLOWED_STATUS = {'created', 'queued', 'running', 'success', 'failed', 'deferred', 'timeout', 'recent', 'feed_recent'}


def _normalize_site_name(site: str) -> str:
    return str(site or '').strip().lower()


def _get_normalized_supported_sites(supported_sites: List[str]) -> List[str]:
    normalized_sites: List[str] = []
    seen: set[str] = set()
    for site in supported_sites:
        normalized_site = _normalize_site_name(site)
        if not normalized_site or normalized_site in seen:
            continue
        seen.add(normalized_site)
        normalized_sites.append(normalized_site)
    return normalized_sites


def _get_supported_site_set(supported_sites: List[str]) -> set[str]:
    return set(_get_normalized_supported_sites(supported_sites))


def _get_enabled_import_sites(supported_sites: List[str]) -> List[str]:
    enabled_sites = SiteCatalog.get_enabled_site_names()
    return [site for site in _get_normalized_supported_sites(supported_sites) if site in enabled_sites]


@router.post("/subscribe")
def subscribe_content(req: SubscribeRequest, current_user: User = Depends(get_current_user)):
    domain = extract_top_level_domain(req.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法订阅")

    subscription = subscription_service.handle_subscribe_request(req.url, current_user.id)
    return response.success({
        'subscription_id': subscription.id,
        'is_subscribed': True,
    })


@router.post("/unsubscribe")
def unsubscribe_content(req: UnsubscribeRequest, current_user: User = Depends(get_current_user)):
    subscription_service.unsubscribe_by_id(current_user.id, req.subscription_id)
    return response.success()


@router.get("/status")
def get_subscription_status(
        url: str = Query(None),
        current_user: User = Depends(get_current_user)
):
    return response.success(subscription_service.check_subscription_status(current_user.id, url))


@router.get("/detail/{subscription_id}")
def get_subscription_detail(subscription_id: int, current_user: User = Depends(get_current_user)):
    """获取订阅（频道）详情，附带当前用户的 is_nsfw 状态和统计字段"""
    sub = subscription_service.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found("订阅不存在")

    is_nsfw = subscription_service.get_user_subscription_nsfw(current_user.id, subscription_id)
    is_special_followed = subscription_service.get_user_subscription_special_followed(current_user.id, subscription_id)
    data = sub.model_dump() if hasattr(sub, 'model_dump') else dict(sub)
    data["is_nsfw"] = bool(is_nsfw) if is_nsfw is not None else False
    data["is_special_followed"] = bool(is_special_followed) if is_special_followed is not None else False
    return response.success(data)


@router.get("/list")
def list_subscriptions(
        query: str = Query(None, description="搜索关键字"),
        type: str = Query(None, description="内容类型"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        special: str = Query("all", description="特别关注过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    domains: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains = resolved if resolved else None

    subscriptions, total = subscription_service.list_subscriptions(
        current_user.id, query, type, nsfw, page, page_size, domains, special
    )
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions
    })


@router.get('/options')
def get_subscription_options(current_user: User = Depends(get_current_user)):
    return response.success({
        'data': subscription_service.list_subscription_options(current_user.id)
    })


@router.get('/sync-center/stream')
async def get_sync_center_stream(
        request: Request,
        selected_run_id: str | None = Query(None, alias='selectedRunId'),
        current_user: User = Depends(get_current_user)
):
    async def event_stream():
        async for event in sync_center_stream_service.stream_sync_center_events(
            user_id=current_user.id,
            selected_run_id=selected_run_id,
        ):
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-store, no-cache, max-age=0, must-revalidate',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@router.post("/{subscription_id}/refresh")
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


@router.post("/{subscription_id}/refresh/direct")
def refresh_subscription_direct(
    subscription_id: int,
    request: Request,
    mode: str = Query('incremental', description='同步模式: incremental|full', pattern=r'^(incremental|full)$'),
    current_user: User = Depends(get_current_user)
):
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

    result = scheduler.run_one_inline(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == 'full' else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id,
    )

    update_result = result.result
    if result.status == 'failed':
        return response.server_error("刷新请求失败")

    return response.success({
        "mode": mode,
        "status": result.status,
        "inProgress": result.status in {'in_progress', 'queued'},
        "subscriptionId": subscription_id,
        "requestId": result.request_id,
        "runId": result.run_id,
        "syncStateId": result.sync_state_id,
        "videosFound": update_result.videos_found if update_result else 0,
        "videosExtracted": update_result.videos_enqueued if update_result else 0,
        "skippedReason": update_result.skipped_reason if update_result else None,
        "hasMore": update_result.has_more if update_result else False,
    })


@router.get('/sync-center/runs')
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
@router.get('/sync-center/runs/{run_id}')
def get_sync_center_run_detail(run_id: str, current_user: User = Depends(get_current_user)):
    result = subscription_sync_history_service.get_run_detail(run_id, current_user.id)
    if not result:
        return response.not_found('运行实例不存在')
    return response.success(result)


@router.get('/sync-center/runs/{run_id}/events')
def get_sync_center_run_events(run_id: str, current_user: User = Depends(get_current_user)):
    events = subscription_sync_history_service.list_run_events(run_id, current_user.id)
    if not events and not subscription_sync_history_service.get_run_detail(run_id, current_user.id):
        return response.not_found('运行实例不存在')
    return response.success(events)
@router.post("/toggle-nsfw")
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


@router.post("/toggle-special-follow")
def toggle_special_follow(
        req: ToggleStatusRequest,
        current_user: User = Depends(get_current_user)
):
    success = subscription_service.toggle_special_follow_status(
        current_user.id,
        req.subscription_id,
        req.is_enable
    )
    return response.success({"success": success})


@router.get("/import/sites")
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


@router.get("/import/{site}/preview")
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
        # API boundary -- convert to HTTP error response
        logger.exception(f"Failed to preview subscriptions from {site}: {e}")
        return response.server_error(f"预览失败: {str(e)}")


@router.post("/import/{site}")
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
        # API boundary -- convert to HTTP error response
        logger.exception(f"Failed to import subscriptions from {site}: {e}")
        return response.server_error(f"导入失败: {str(e)}")
