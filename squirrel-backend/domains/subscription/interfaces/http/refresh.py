from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.update.models import UpdateMode, UpdateTrigger
from domains.subscription.application.services.core.update.scheduler import SubscriptionScheduler
from domains.subscription.interfaces.http.dependencies import (
    get_subscription_crud_service,
    get_subscription_scheduler,
)
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain

router = APIRouter()


@router.post('/{subscription_id}/refresh')
def refresh_subscription(
    subscription_id: int,
    request: Request,
    mode: str = Query('incremental', description='Sync mode: incremental|full', pattern=r'^(incremental|full)$'),
    current_user: CurrentUserDto = Depends(get_current_user),
    crud_svc: SubscriptionCrudService = Depends(get_subscription_crud_service),
    subscription_scheduler: SubscriptionScheduler = Depends(get_subscription_scheduler),
):
    """Manually refresh subscription
    Responsibility: validate permissions then call scheduler; actual update logic handled by scheduler and orchestrator
    """
    subscription, status = crud_svc.verify_subscription_access(current_user.id, subscription_id)
    if status == 'not_found':
        return response.not_found('订阅不存在')
    if status == 'forbidden':
        return response.forbidden('无权操作该订阅')

    domain = extract_top_level_domain(subscription.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error('站点插件未启用,无法刷新订阅')

    trace_id = getattr(request.state, 'trace_id', None)

    schedule_result = subscription_scheduler.schedule_one(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == 'full' else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id,
    )

    if schedule_result.status == 'failed':
        return response.server_error('刷新请求失败')

    return response.success(
        {
            'mode': mode,
            'status': schedule_result.status,
            'inProgress': schedule_result.status == 'in_progress',
            'subscriptionId': subscription_id,
            'requestId': schedule_result.request_id,
            'queuedAt': datetime.utcnow().isoformat() if schedule_result.status == 'queued' else None,
        }
    )


@router.post('/{subscription_id}/refresh/direct')
def refresh_subscription_direct(
    subscription_id: int,
    request: Request,
    mode: str = Query('incremental', description='Sync mode: incremental|full', pattern=r'^(incremental|full)$'),
    current_user: CurrentUserDto = Depends(get_current_user),
    crud_svc: SubscriptionCrudService = Depends(get_subscription_crud_service),
    subscription_scheduler: SubscriptionScheduler = Depends(get_subscription_scheduler),
):
    subscription, status = crud_svc.verify_subscription_access(current_user.id, subscription_id)
    if status == 'not_found':
        return response.not_found('订阅不存在')
    if status == 'forbidden':
        return response.forbidden('无权操作该订阅')

    domain = extract_top_level_domain(subscription.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error('站点插件未启用,无法刷新订阅')

    trace_id = getattr(request.state, 'trace_id', None)

    run_result = subscription_scheduler.run_one_inline(
        subscription_id=subscription.id,
        url=subscription.url,
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL if mode == 'full' else UpdateMode.INCREMENTAL,
        user_id=current_user.id,
        trace_id=trace_id,
    )

    update_result = run_result.result
    if run_result.status == 'failed':
        return response.server_error('刷新请求失败')

    return response.success(
        {
            'mode': mode,
            'status': run_result.status,
            'inProgress': run_result.status in {'in_progress', 'queued'},
            'subscriptionId': subscription_id,
            'requestId': run_result.request_id,
            'runId': run_result.run_id,
            'syncStateId': run_result.sync_state_id,
            'videosFound': update_result.videos_found if update_result else 0,
            'videosExtracted': update_result.videos_enqueued if update_result else 0,
            'skippedReason': update_result.skipped_reason if update_result else None,
            'hasMore': update_result.has_more if update_result else False,
        }
    )
