from fastapi import APIRouter, Depends, Query

from domains.subscription.application.services.core.crud import subscription_crud_service
from domains.subscription.application.services.core.import_service import subscription_import_service
from domains.subscription.application.services.core.listing.service import subscription_list_service
from domains.subscription.application.services.core.manage import subscription_manage_service
from domains.subscription.interfaces.dto.request.subscription import (
    SubscribeRequest,
    ToggleStatusRequest,
    UnsubscribeRequest,
)
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain

router = APIRouter()


@router.post('/subscribe')
def subscribe_content(
    req: SubscribeRequest,
    current_user: User = Depends(get_current_user),
):
    domain = extract_top_level_domain(req.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error('站点插件未启用,无法订阅')

    subscription = subscription_import_service.handle_subscribe_request(req.url, current_user.id)
    return response.success(
        {
            'subscription_id': subscription.id,
            'is_subscribed': True,
        }
    )


@router.post('/unsubscribe')
def unsubscribe_content(
    req: UnsubscribeRequest,
    current_user: User = Depends(get_current_user),
):
    subscription_manage_service.unsubscribe_by_id(current_user.id, req.subscription_id)
    return response.success()


@router.get('/status')
def get_subscription_status(
    url: str = Query(None),
    current_user: User = Depends(get_current_user),
):
    return response.success(subscription_crud_service.check_subscription_status(current_user.id, url))


@router.get('/detail/{subscription_id}')
def get_subscription_detail(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get subscription (channel) details with current user's is_nsfw status and stats"""
    sub = subscription_list_service.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found('订阅不存在')

    is_nsfw = subscription_crud_service.get_user_subscription_nsfw(current_user.id, subscription_id)
    is_special_followed = subscription_crud_service.get_user_subscription_special_followed(
        current_user.id,
        subscription_id,
    )
    data = sub.model_dump() if hasattr(sub, 'model_dump') else dict(sub)
    data['is_nsfw'] = bool(is_nsfw) if is_nsfw is not None else False
    data['is_special_followed'] = bool(is_special_followed) if is_special_followed is not None else False
    return response.success(data)


@router.get('/list')
def list_subscriptions(
    query: str = Query(None, description='Search keyword'),
    type: str = Query(None, description='Content type'),
    nsfw: str = Query('all', description='NSFW filter: all|yes|no', pattern=r'^(all|yes|no)$'),
    special: str = Query('all', description='Special follow filter: all|yes|no', pattern=r'^(all|yes|no)$'),
    site: str = Query(None, description='Site filter: e.g. youtube, bilibili (supports aliases)'),
    page: int = Query(1, ge=1, description='Page number'),
    page_size: int = Query(10, ge=1, le=100, alias='pageSize', description='Page size'),
    current_user: User = Depends(get_current_user),
):
    domains: list[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains = resolved or None

    subscriptions, total = subscription_list_service.list_subscriptions(
        current_user.id,
        query,
        type,
        nsfw,
        page,
        page_size,
        domains,
        special,
    )
    return response.success(
        {
            'total': total,
            'page': page,
            'pageSize': page_size,
            'data': subscriptions,
        }
    )


@router.get('/options')
def get_subscription_options(
    current_user: User = Depends(get_current_user),
):
    return response.success(
        {
            'data': subscription_list_service.list_subscription_options(current_user.id),
        }
    )


@router.post('/toggle-nsfw')
def toggle_nsfw(
    req: ToggleStatusRequest,
    current_user: User = Depends(get_current_user),
):
    success = subscription_manage_service.toggle_nsfw_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({'success': success})


@router.post('/toggle-special-follow')
def toggle_special_follow(
    req: ToggleStatusRequest,
    current_user: User = Depends(get_current_user),
):
    success = subscription_manage_service.toggle_special_follow_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({'success': success})
