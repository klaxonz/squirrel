import pytest

from domains.subscription.application.services.core.import_errors import SubscriptionImportError
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from infrastructure.site_plugins.registry import SitePluginError, SitePluginResult


class _FailingRegistry:
    def __init__(self, result: SitePluginResult) -> None:
        self.result = result
        self.calls = []

    def invoke(self, capability, payload=None, site_name=None, domain=None):
        self.calls.append((capability, payload, site_name, domain))
        return self.result


def test_import_batch_preserves_retryable_plugin_failure_classification():
    registry = _FailingRegistry(
        SitePluginResult(
            ok=False,
            error=SitePluginError(
                message='rate limited',
                code='PLUGIN_NETWORK_ERROR',
                details={'error_category': 'rate_limit', 'retry_after_seconds': 23},
                retryable=True,
            ),
            retryable=True,
        ),
    )
    service = SubscriptionImportService(registry=registry)

    with pytest.raises(SubscriptionImportError) as exc_info:
        service._load_plugin_import_batch('youtube')

    assert exc_info.value.retryable is True
    assert exc_info.value.error_type == 'PLUGIN_NETWORK_ERROR'
    assert exc_info.value.retry_after_seconds == 23


def test_subscription_resolution_preserves_non_retryable_plugin_failure_classification():
    registry = _FailingRegistry(
        SitePluginResult(
            ok=False,
            error=SitePluginError(
                message='login required',
                code='PLUGIN_AUTH_REQUIRED',
                details={},
                retryable=False,
            ),
        ),
    )

    class _NoExistingSubscription:
        @staticmethod
        def get_active_user_subscription_by_url(*, user_id, url):
            return None

        @staticmethod
        def get_subscription_by_url(url):
            return None

    service = SubscriptionImportService(
        registry=registry,
        crud_service=_NoExistingSubscription(),
        manage_service=object(),
    )

    with pytest.raises(SubscriptionImportError) as exc_info:
        service.process_import_payload(
            {
                'url': 'https://www.youtube.com/@demo',
                'user_id': 7,
                'expected_intent_version': 0,
            },
        )

    assert exc_info.value.retryable is False
    assert exc_info.value.error_type == 'PLUGIN_AUTH_REQUIRED'
    assert exc_info.value.retry_after_seconds is None
