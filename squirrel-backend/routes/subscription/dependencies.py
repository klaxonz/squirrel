from services.subscription.sync.history_service import SubscriptionSyncHistoryService
from services.sync_dashboard.stream_service import SyncDashboardStreamService


def get_sync_history_service() -> SubscriptionSyncHistoryService:
    return SubscriptionSyncHistoryService()


def get_stream_service() -> SyncDashboardStreamService:
    return SyncDashboardStreamService()
