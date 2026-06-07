import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from common import response
from models.user import User
from schemas.subscription.request.subscription import (
    ImportSubscriptionsRequest,
    SubscribeRequest,
    ToggleStatusRequest,
    UnsubscribeRequest,
)
from services.subscription_service import SubscriptionService
from services.subscription_sync_history_service import SubscriptionSyncHistoryService
from services.sync_center_stream_service import SyncCenterStreamService
from utils.jwt_helper import get_current_user
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

router = APIRouter(prefix="/api/subscription", tags=["Subscription API"])
logger = logging.getLogger(__name__)
SYNC_HISTORY_ALLOWED_STATUS = {"created", "queued", "running", "success", "failed", "deferred", "timeout", "recent", "feed_recent"}


def get_subscription_service() -> SubscriptionService:
    return SubscriptionService()


def get_sync_history_service() -> SubscriptionSyncHistoryService:
    return SubscriptionSyncHistoryService()


def get_stream_service() -> SyncCenterStreamService:
    return SyncCenterStreamService()


def _normalize_site_name(site: str) -> str:
    return str(site or "").strip().lower()


def _get_normalized_supported_sites(supported_sites: list[str]) -> list[str]:
    normalized_sites: list[str] = []
    seen: set[str] = set()
    for site in supported_sites:
        normalized_site = _normalize_site_name(site)
        if not normalized_site or normalized_site in seen:
            continue
        seen.add(normalized_site)
        normalized_sites.append(normalized_site)
    return normalized_sites


def _get_supported_site_set(supported_sites: list[str]) -> set[str]:
    return set(_get_normalized_supported_sites(supported_sites))


def _get_enabled_import_sites(supported_sites: list[str]) -> list[str]:
    enabled_sites = SiteCatalog.get_enabled_site_names()
    return [site for site in _get_normalized_supported_sites(supported_sites) if site in enabled_sites]


@router.post("/subscribe")
def subscribe_content(
        req: SubscribeRequest,
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    domain = extract_top_level_domain(req.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法订阅")

    subscription = svc.handle_subscribe_request(req.url, current_user.id)
    return response.success({
        "subscription_id": subscription.id,
        "is_subscribed": True,
    })


@router.post("/unsubscribe")
def unsubscribe_content(
        req: UnsubscribeRequest,
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    svc.unsubscribe_by_id(current_user.id, req.subscription_id)
    return response.success()


@router.get("/status")
def get_subscription_status(
        url: str = Query(None),
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    return response.success(svc.check_subscription_status(current_user.id, url))


@router.get("/detail/{subscription_id}")
def get_subscription_detail(
        subscription_id: int,
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    """Get subscription (channel) details with current user's is_nsfw status and stats"""
    sub = svc.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found("订阅不存在")

    is_nsfw = svc.get_user_subscription_nsfw(current_user.id, subscription_id)
    is_special_followed = svc.get_user_subscription_special_followed(current_user.id, subscription_id)
    data = sub.model_dump() if hasattr(sub, "model_dump") else dict(sub)
    data["is_nsfw"] = bool(is_nsfw) if is_nsfw is not None else False
    data["is_special_followed"] = bool(is_special_followed) if is_special_followed is not None else False
    return response.success(data)


@router.get("/list")
def list_subscriptions(
        query: str = Query(None, description="Search keyword"),
        type: str = Query(None, description="Content type"),
        nsfw: str = Query("all", description="NSFW filter: all|yes|no", pattern=r"^(all|yes|no)$"),
        special: str = Query("all", description="Special follow filter: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="Site filter: e.g. youtube, bilibili (supports aliases)"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Page size"),
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    domains: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains = resolved or None

    subscriptions, total = svc.list_subscriptions(
        current_user.id, query, type, nsfw, page, page_size, domains, special,
    )
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": subscriptions,
    })


@router.get("/options")
def get_subscription_options(
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    return response.success({
        "data": svc.list_subscription_options(current_user.id),
    })


@router.get("/sync-center/stream")
async def get_sync_center_stream(
        request: Request,
        selected_run_id: str | None = Query(None, alias="selectedRunId"),
        current_user: User = Depends(get_current_user),
        stream_svc: SyncCenterStreamService = Depends(get_stream_service),
):
    async def event_stream():
        async for event in stream_svc.stream_sync_center_events(
            user_id=current_user.id,
            selected_run_id=selected_run_id,
        ):
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{subscription_id}/refresh")
def refresh_subscription(
    subscription_id: int,
    request: Request,
    mode: str = Query("incremental", description="Sync mode: incremental|full", pattern=r"^(incremental|full)$"),
    current_user: User = Depends(get_current_user),
    svc: SubscriptionService = Depends(get_subscription_service),
):
    """Manually refresh subscription
    Responsibility: validate permissions then call scheduler; actual update logic handled by scheduler and orchestrator
    """
    subscription, status = svc.verify_subscription_access(current_user.id, subscription_id)
    if status == "not_found":
        return response.not_found("订阅不存在")
    if status == "forbidden":
        return response.forbidden("无权操作该订阅")

    domain = extract_top_level_domain(subscription.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法刷新订阅")

    from services.subscription_update import UpdateMode, UpdateTrigger, scheduler

    trace_id = getattr(request.state, "trace_id", None)

    result = scheduler.schedule_one(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == "full" else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id,
    )

    if result.status == "failed":
        return response.server_error("刷新请求失败")

    return response.success({
        "mode": mode,
        "status": result.status,
        "inProgress": result.status == "in_progress",
        "subscriptionId": subscription_id,
        "requestId": result.request_id,
        "queuedAt": datetime.utcnow().isoformat() if result.status == "queued" else None,
    })


@router.post("/{subscription_id}/refresh/direct")
def refresh_subscription_direct(
    subscription_id: int,
    request: Request,
    mode: str = Query("incremental", description="Sync mode: incremental|full", pattern=r"^(incremental|full)$"),
    current_user: User = Depends(get_current_user),
    svc: SubscriptionService = Depends(get_subscription_service),
):
    subscription, status = svc.verify_subscription_access(current_user.id, subscription_id)
    if status == "not_found":
        return response.not_found("订阅不存在")
    if status == "forbidden":
        return response.forbidden("无权操作该订阅")

    domain = extract_top_level_domain(subscription.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error("站点插件未启用，无法刷新订阅")

    from services.subscription_update import UpdateMode, UpdateTrigger, scheduler

    trace_id = getattr(request.state, "trace_id", None)

    result = scheduler.run_one_inline(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == "full" else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id,
    )

    update_result = result.result
    if result.status == "failed":
        return response.server_error("刷新请求失败")

    return response.success({
        "mode": mode,
        "status": result.status,
        "inProgress": result.status in {"in_progress", "queued"},
        "subscriptionId": subscription_id,
        "requestId": result.request_id,
        "runId": result.run_id,
        "syncStateId": result.sync_state_id,
        "videosFound": update_result.videos_found if update_result else 0,
        "videosExtracted": update_result.videos_enqueued if update_result else 0,
        "skippedReason": update_result.skipped_reason if update_result else None,
        "hasMore": update_result.has_more if update_result else False,
    })


@router.get("/sync-center/runs")
def get_sync_center_runs(
        status: str = Query(None, description="Run status filter"),
        site: str = Query(None, description="Site filter"),
        subscription_id: int = Query(None, alias="subscriptionId", description="Channel filter"),
        mode: str = Query(None, description="Sync mode filter"),
        trigger: str = Query(None, description="Trigger type filter"),
        date_from: str = Query(None, alias="dateFrom", description="Start date"),
        date_to: str = Query(None, alias="dateTo", description="End date"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="Page size"),
        current_user: User = Depends(get_current_user),
        sync_history_svc: SubscriptionSyncHistoryService = Depends(get_sync_history_service),
):
    normalized_status = str(status or "").strip().lower() or None
    if normalized_status and normalized_status not in SYNC_HISTORY_ALLOWED_STATUS:
        return response.param_error(f"不支持的运行状态筛选: {status}")

    result = sync_history_svc.list_runs(
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
@router.get("/sync-center/runs/{run_id}")
def get_sync_center_run_detail(
        run_id: str,
        current_user: User = Depends(get_current_user),
        sync_history_svc: SubscriptionSyncHistoryService = Depends(get_sync_history_service),
):
    result = sync_history_svc.get_run_detail(run_id, current_user.id)
    if not result:
        return response.not_found("运行实例不存在")
    return response.success(result)


@router.get("/sync-center/runs/{run_id}/events")
def get_sync_center_run_events(
        run_id: str,
        current_user: User = Depends(get_current_user),
        sync_history_svc: SubscriptionSyncHistoryService = Depends(get_sync_history_service),
):
    events = sync_history_svc.list_run_events(run_id, current_user.id)
    if not events and not sync_history_svc.get_run_detail(run_id, current_user.id):
        return response.not_found("运行实例不存在")
    return response.success(events)
@router.post("/toggle-nsfw")
def toggle_nsfw(
        req: ToggleStatusRequest,
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    success = svc.toggle_nsfw_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({"success": success})


@router.post("/toggle-special-follow")
def toggle_special_follow(
        req: ToggleStatusRequest,
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    success = svc.toggle_special_follow_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({"success": success})


@router.get("/import/sites")
def get_supported_sites(
        current_user: User = Depends(get_current_user),
        svc: SubscriptionService = Depends(get_subscription_service),
):
    """Get list of sites supported for import

    Returns:
        List of supported sites

    """
    supported_sites = svc.get_runtime_supported_sites("import_subscriptions")
    enabled_sites = _get_enabled_import_sites(supported_sites)

    return response.success({
        "sites": enabled_sites,
    })


@router.get("/import/{site}/preview")
def preview_subscriptions(
    site: str,
    cursor: str | None = Query(None, description="Pagination cursor JSON"),
    limit: int = Query(50, ge=1, le=200, description="Preview page size"),
    current_user: User = Depends(get_current_user),
    svc: SubscriptionService = Depends(get_subscription_service),
):
    """Preview user's subscriptions at a given site (without actually importing)

    Args:
        site: Site name

    Returns:
        Preview result

    """
    try:
        supported_sites = svc.get_runtime_supported_sites("import_subscriptions")
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
                raise ValueError(f"无效的预览游标: {exc.msg}") from exc
            if not isinstance(parsed_cursor, dict):
                raise ValueError("无效的预览游标: 必须为 JSON object")
            cursor_payload = parsed_cursor

        logger.info("User %s previewing subscriptions from %s", current_user.id, normalized_site)

        result = svc.preview_user_subscriptions(
            normalized_site,
            current_user.id,
            cursor_payload=cursor_payload,
            limit=limit,
        )

        return response.success(result)

    except ValueError as e:
        logger.error("Invalid request for site %s: %s", site, e)
        return response.param_error(str(e))
    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to preview subscriptions from %s: %s", site, e)
        return response.server_error(f"预览失败: {e!s}")


@router.post("/import/{site}")
def import_subscriptions(
    site: str,
    req: ImportSubscriptionsRequest | None = None,
    current_user: User = Depends(get_current_user),
    svc: SubscriptionService = Depends(get_subscription_service),
):
    """Import all user subscriptions from a specified site

    Args:
        site: Site name (dynamically supports all registered sites)

    Returns:
        Import result statistics

    """
    try:
        supported_sites = svc.get_runtime_supported_sites("import_subscriptions")
        supported_site_set = _get_supported_site_set(supported_sites)
        normalized_site = _normalize_site_name(site)
        enabled_sites = _get_enabled_import_sites(supported_sites)

        if normalized_site not in supported_site_set:
            return response.param_error(f"不支持的站点: {site}，支持的站点: {', '.join(supported_sites)}")
        if normalized_site not in enabled_sites:
            return response.param_error(f"站点已禁用，无法导入订阅: {site}")

        logger.info("User %s importing subscriptions from %s", current_user.id, normalized_site)

        selected_urls = req.subscription_urls if req else None
        result = svc.import_user_subscriptions(normalized_site, current_user.id, selected_urls=selected_urls)

        return response.success({
            "site": normalized_site,
            "total": result["total"],
            "found": result["found"],
            "selected": result["selected"],
            "skipped": result["skipped"],
        })

    except ValueError as e:
        logger.error("Invalid request for site %s: %s", site, e)
        return response.param_error(str(e))
    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to import subscriptions from %s: %s", site, e)
        return response.server_error(f"导入失败: {e!s}")
