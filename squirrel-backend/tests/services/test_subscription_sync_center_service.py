def test_sync_center_service_can_be_instantiated():
    from services.subscription_sync_center_service import SubscriptionSyncCenterService
    svc = SubscriptionSyncCenterService()
    assert svc is not None
