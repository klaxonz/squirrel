from fastapi import APIRouter, Depends, Query

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.subscription.interfaces.dto.request.subscription import (
    SubscribeRequest,
    SubscriptionListQuery,
    ToggleStatusRequest,
    UnsubscribeRequest,
)
from domains.subscription.interfaces.http.dependencies import (
    get_subscription_crud_service,
    get_subscription_import_service,
    get_subscription_list_service,
    get_subscription_manage_service,
)
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain

router = APIRouter()


@router.post('/subscribe')
def subscribe_content(
    req: SubscribeRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    import_svc: SubscriptionImportService = Depends(get_subscription_import_service),
):
    domain = extract_top_level_domain(req.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        return response.param_error('站点插件未启用,无法订阅')

    subscription = import_svc.handle_subscribe_request(req.url, current_user.id)
    return response.success(
        {
            'subscription_id': subscription.id,
            'is_subscribed': True,
        }
    )


@router.post('/unsubscribe')
def unsubscribe_content(
    req: UnsubscribeRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    manage_svc: SubscriptionManageService = Depends(get_subscription_manage_service),
):
    manage_svc.unsubscribe_by_id(current_user.id, req.subscription_id)
    return response.success()


@router.get('/status')
def get_subscription_status(
    url: str = Query(None),
    current_user: CurrentUserDto = Depends(get_current_user),
    crud_svc: SubscriptionCrudService = Depends(get_subscription_crud_service),
):
    return response.success(crud_svc.check_subscription_status(current_user.id, url))


@router.get('/detail/{subscription_id}')
def get_subscription_detail(
    subscription_id: int,
    current_user: CurrentUserDto = Depends(get_current_user),
    crud_svc: SubscriptionCrudService = Depends(get_subscription_crud_service),
    list_svc: SubscriptionListService = Depends(get_subscription_list_service),
):
    """Get subscription (channel) details with current user's is_nsfw status and stats"""
    sub = list_svc.get_subscription_detail(subscription_id)
    if not sub:
        return response.not_found('订阅不存在')

    is_nsfw = crud_svc.get_user_subscription_nsfw(current_user.id, subscription_id)
    is_special_followed = crud_svc.get_user_subscription_special_followed(
        current_user.id,
        subscription_id,
    )
    data = sub.model_dump() if hasattr(sub, 'model_dump') else dict(sub)
    data['is_nsfw'] = bool(is_nsfw) if is_nsfw is not None else False
    data['is_special_followed'] = bool(is_special_followed) if is_special_followed is not None else False
    return response.success(data)


@router.get('/list')
def list_subscriptions(
    params: SubscriptionListQuery = Depends(),
    current_user: CurrentUserDto = Depends(get_current_user),
    list_svc: SubscriptionListService = Depends(get_subscription_list_service),
):
    domains: list[str] | None = None
    if params.site:
        resolved = SiteCatalog.resolve_domains(params.site)
        domains = resolved or None

    subscriptions, total = list_svc.list_subscriptions(
        current_user.id,
        params.query,
        params.type,
        params.nsfw,
        params.page,
        params.page_size,
        domains,
        params.special,
    )
    return response.success(
        {
            'total': total,
            'page': params.page,
            'pageSize': params.page_size,
            'data': subscriptions,
        }
    )


@router.get('/options')
def get_subscription_options(
    current_user: CurrentUserDto = Depends(get_current_user),
    list_svc: SubscriptionListService = Depends(get_subscription_list_service),
):
    return response.success(
        {
            'data': list_svc.list_subscription_options(current_user.id),
        }
    )


@router.post('/toggle-nsfw')
def toggle_nsfw(
    req: ToggleStatusRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    manage_svc: SubscriptionManageService = Depends(get_subscription_manage_service),
):
    success = manage_svc.toggle_nsfw_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({'success': success})


@router.post('/toggle-special-follow')
def toggle_special_follow(
    req: ToggleStatusRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    manage_svc: SubscriptionManageService = Depends(get_subscription_manage_service),
):
    success = manage_svc.toggle_special_follow_status(
        current_user.id,
        req.subscription_id,
        req.is_enable,
    )
    return response.success({'success': success})
