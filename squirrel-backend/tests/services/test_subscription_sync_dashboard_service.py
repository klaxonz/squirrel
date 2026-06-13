def test_sync_dashboard_service_can_be_instantiated():
    from services.subscription.sync.dashboard_service import SubscriptionSyncDashboardService
    svc = SubscriptionSyncDashboardService()
    assert svc is not None
