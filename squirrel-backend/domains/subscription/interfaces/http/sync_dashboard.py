from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from shared_kernel.application import response
from domains.user.domain.models.user import User
from domains.subscription.application.services.core.sync.history_service import SubscriptionSyncHistoryService
from domains.subscription.application.services.sync.stream_service import SyncDashboardStreamService
from domains.user.application.services.auth import get_current_user

from .dependencies import get_stream_service, get_sync_history_service

router = APIRouter()
SYNC_HISTORY_ALLOWED_STATUS = {'created', 'queued', 'running', 'success', 'failed', 'deferred', 'timeout', 'recent', 'feed_recent'}

@router.get("/sync-center/stream")
async def get_sync_dashboard_stream(
        request: Request,
        selected_run_id: str | None = Query(None, alias="selectedRunId"),
        current_user: User = Depends(get_current_user),
        stream_svc: SyncDashboardStreamService = Depends(get_stream_service),
):
    async def event_stream():
        async for event in stream_svc.stream_sync_dashboard_events(
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


@router.get("/sync-center/runs")
def get_sync_dashboard_runs(
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

    history_result = sync_history_svc.list_runs(
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
    return response.success(history_result)


@router.get("/sync-center/runs/{run_id}")
def get_sync_dashboard_run_detail(
        run_id: str,
        current_user: User = Depends(get_current_user),
        sync_history_svc: SubscriptionSyncHistoryService = Depends(get_sync_history_service),
):
    detail_result = sync_history_svc.get_run_detail(run_id, current_user.id)
    if not detail_result:
        return response.not_found("运行实例不存在")
    return response.success(detail_result)


@router.get("/sync-center/runs/{run_id}/events")
def get_sync_dashboard_run_events(
        run_id: str,
        current_user: User = Depends(get_current_user),
        sync_history_svc: SubscriptionSyncHistoryService = Depends(get_sync_history_service),
):
    events = sync_history_svc.list_run_events(run_id, current_user.id)
    if not events and not sync_history_svc.get_run_detail(run_id, current_user.id):
        return response.not_found("运行实例不存在")
    return response.success(events)
