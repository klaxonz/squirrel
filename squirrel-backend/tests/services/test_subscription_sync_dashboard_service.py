def test_sync_dashboard_service_can_be_instantiated():
    from domains.subscription.application.services.core.sync.dashboard_service import SubscriptionSyncDashboardService
    svc = SubscriptionSyncDashboardService()
    assert svc is not None
