from domains.subscription.application.services.core.crud import SubscriptionCrudService, subscription_crud_service
from domains.subscription.application.services.core.import_service import (
    SubscriptionImportService,
    subscription_import_service,
)
from domains.subscription.application.services.core.listing.service import (
    SubscriptionListService,
    subscription_list_service,
)
from domains.subscription.application.services.core.manage import SubscriptionManageService, subscription_manage_service
from domains.subscription.application.services.core.update.scheduler import SubscriptionScheduler, scheduler


def get_subscription_crud_service() -> SubscriptionCrudService:
    return subscription_crud_service


def get_subscription_import_service() -> SubscriptionImportService:
    return subscription_import_service


def get_subscription_list_service() -> SubscriptionListService:
    return subscription_list_service


def get_subscription_manage_service() -> SubscriptionManageService:
    return subscription_manage_service


def get_subscription_scheduler() -> SubscriptionScheduler:
    return scheduler
