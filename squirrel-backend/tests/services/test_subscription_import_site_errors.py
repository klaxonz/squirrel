import pytest

from domains.subscription.application.services.core.import_errors import SubscriptionImportError
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from sites.crawl import AuthError, RateLimitError


class _FailingSite:
    def __init__(self, exc) -> None:
        self.exc = exc

    def import_subscriptions(self, **kwargs):
        raise self.exc

    def resolve_subscription(self, url, **kwargs):
        raise self.exc


class _FailingRegistry:
    def __init__(self, exc) -> None:
        self.exc = exc
        self.calls = []

    def get_site_runtime(self, site_name):
        self.calls.append(site_name)
        return _FailingSite(self.exc)

    def find_site_by_domain(self, domain):
        return 'youtube'


def test_import_batch_preserves_retryable_rate_limit_classification():
    registry = _FailingRegistry(RateLimitError('rate limited', retry_after=23))
    service = SubscriptionImportService(registry=registry)

    with pytest.raises(SubscriptionImportError) as exc_info:
        service._load_site_import_batch('youtube')

    assert exc_info.value.retryable is True
    assert exc_info.value.error_type == 'rate_limit'
    assert exc_info.value.retry_after_seconds == 23


def test_subscription_resolution_preserves_non_retryable_auth_classification():
    registry = _FailingRegistry(AuthError('login required'))

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
    assert exc_info.value.error_type == 'auth'
    assert exc_info.value.retry_after_seconds is None
