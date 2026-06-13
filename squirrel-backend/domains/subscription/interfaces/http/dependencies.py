from domains.subscription.application.services.core.sync.history_service import SubscriptionSyncHistoryService
from domains.subscription.application.services.sync.stream_service import SyncDashboardStreamService


def get_sync_history_service() -> SubscriptionSyncHistoryService:
    return SubscriptionSyncHistoryService()


def get_stream_service() -> SyncDashboardStreamService:
    return SyncDashboardStreamService()
