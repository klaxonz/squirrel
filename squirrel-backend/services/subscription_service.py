from services.subscription_crud_service import (
    check_subscription_status,
    get_active_user_subscription_by_url,
    get_active_user_subscription_url_map,
    get_deleted_user_subscription_urls,
    get_subscription_by_id,
    get_subscription_by_url_and_name,
    get_user_subscription_nsfw,
    get_user_subscription_special_followed,
    toggle_status,
    update_subscription,
    verify_subscription_access,
)
from services.subscription_import_service import (
    auto_import_missing_subscriptions,
    get_enabled_runtime_import_sites,
    get_runtime_supported_sites,
    handle_subscribe_request,
    import_user_subscriptions,
    preview_user_subscriptions,
)
from services.subscription_list_service import (
    get_subscription_detail,
    list_subscription_options,
    list_subscriptions,
)
from services.subscription_manage_service import (
    create_subscribe_message,
    create_subscription,
    list_user_ids,
    restore_subscription,
    toggle_nsfw_status,
    toggle_special_follow_status,
    unsubscribe_by_id,
)

__all__ = [
    "auto_import_missing_subscriptions",
    "check_subscription_status",
    "create_subscribe_message",
    "create_subscription",
    "get_active_user_subscription_by_url",
    "get_active_user_subscription_url_map",
    "get_deleted_user_subscription_urls",
    "get_enabled_runtime_import_sites",
    "get_runtime_supported_sites",
    "get_subscription_by_id",
    "get_subscription_by_url_and_name",
    "get_subscription_detail",
    "get_user_subscription_nsfw",
    "get_user_subscription_special_followed",
    "handle_subscribe_request",
    "import_user_subscriptions",
    "list_subscription_options",
    "list_subscriptions",
    "list_user_ids",
    "preview_user_subscriptions",
    "restore_subscription",
    "toggle_nsfw_status",
    "toggle_special_follow_status",
    "toggle_status",
    "unsubscribe_by_id",
    "update_subscription",
    "verify_subscription_access",
]


class SubscriptionService:
    @staticmethod
    def auto_import_missing_subscriptions(*args, **kwargs):
        return auto_import_missing_subscriptions(*args, **kwargs)

    @staticmethod
    def check_subscription_status(*args, **kwargs):
        return check_subscription_status(*args, **kwargs)

    @staticmethod
    def create_subscribe_message(*args, **kwargs):
        return create_subscribe_message(*args, **kwargs)

    @staticmethod
    def create_subscription(*args, **kwargs):
        return create_subscription(*args, **kwargs)

    @staticmethod
    def get_active_user_subscription_by_url(*args, **kwargs):
        return get_active_user_subscription_by_url(*args, **kwargs)

    @staticmethod
    def get_active_user_subscription_url_map(*args, **kwargs):
        return get_active_user_subscription_url_map(*args, **kwargs)

    @staticmethod
    def get_deleted_user_subscription_urls(*args, **kwargs):
        return get_deleted_user_subscription_urls(*args, **kwargs)

    @staticmethod
    def get_enabled_runtime_import_sites(*args, **kwargs):
        return get_enabled_runtime_import_sites(*args, **kwargs)

    @staticmethod
    def get_runtime_supported_sites(*args, **kwargs):
        return get_runtime_supported_sites(*args, **kwargs)

    @staticmethod
    def get_subscription_by_id(*args, **kwargs):
        return get_subscription_by_id(*args, **kwargs)

    @staticmethod
    def get_subscription_by_url_and_name(*args, **kwargs):
        return get_subscription_by_url_and_name(*args, **kwargs)

    @staticmethod
    def get_subscription_detail(*args, **kwargs):
        return get_subscription_detail(*args, **kwargs)

    @staticmethod
    def get_user_subscription_nsfw(*args, **kwargs):
        return get_user_subscription_nsfw(*args, **kwargs)

    @staticmethod
    def get_user_subscription_special_followed(*args, **kwargs):
        return get_user_subscription_special_followed(*args, **kwargs)

    @staticmethod
    def handle_subscribe_request(*args, **kwargs):
        return handle_subscribe_request(*args, **kwargs)

    @staticmethod
    def import_user_subscriptions(*args, **kwargs):
        return import_user_subscriptions(*args, **kwargs)

    @staticmethod
    def list_subscription_options(*args, **kwargs):
        return list_subscription_options(*args, **kwargs)

    @staticmethod
    def list_subscriptions(*args, **kwargs):
        return list_subscriptions(*args, **kwargs)

    @staticmethod
    def list_user_ids(*args, **kwargs):
        return list_user_ids(*args, **kwargs)

    @staticmethod
    def preview_user_subscriptions(*args, **kwargs):
        return preview_user_subscriptions(*args, **kwargs)

    @staticmethod
    def restore_subscription(*args, **kwargs):
        return restore_subscription(*args, **kwargs)

    @staticmethod
    def toggle_nsfw_status(*args, **kwargs):
        return toggle_nsfw_status(*args, **kwargs)

    @staticmethod
    def toggle_special_follow_status(*args, **kwargs):
        return toggle_special_follow_status(*args, **kwargs)

    @staticmethod
    def toggle_status(*args, **kwargs):
        return toggle_status(*args, **kwargs)

    @staticmethod
    def unsubscribe_by_id(*args, **kwargs):
        return unsubscribe_by_id(*args, **kwargs)

    @staticmethod
    def update_subscription(*args, **kwargs):
        return update_subscription(*args, **kwargs)

    @staticmethod
    def verify_subscription_access(*args, **kwargs):
        return verify_subscription_access(*args, **kwargs)
