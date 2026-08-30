from fastapi import Request

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.subscription.application.services.core.update.scheduler import SubscriptionScheduler
from domains.subscription.application.services.service import SubscriptionService


def _get_subscription_service(request: Request) -> SubscriptionService:
    return request.app.state.subscription_service


def get_subscription_crud_service(request: Request) -> SubscriptionCrudService:
    return _get_subscription_service(request).crud_service


def get_subscription_import_service(request: Request) -> SubscriptionImportService:
    return _get_subscription_service(request).import_service


def get_subscription_list_service(request: Request) -> SubscriptionListService:
    return _get_subscription_service(request).list_service


def get_subscription_manage_service(request: Request) -> SubscriptionManageService:
    return _get_subscription_service(request).manage_service


def get_subscription_scheduler(request: Request) -> SubscriptionScheduler:
    return _get_subscription_service(request).scheduler_service
