"""Tests for CrawlDispatcherPolicy, especially from_settings() reading CrawlSettings.

The broader dispatcher service tests construct policies with literal dicts directly;
these tests pin the wiring between CrawlSettings (grouped sub-model) and the policy.
"""

from __future__ import annotations

from unittest.mock import patch

from domains.subscription.application.services.crawl.dispatcher.policy import CrawlDispatcherPolicy


class _FakeCrawlSettings:
    def __init__(
        self,
        *,
        default_site_concurrency: int = 2,
        site_concurrency_overrides: dict[str, int] | None = None,
        task_type_limits: dict[str, int] | None = None,
    ):
        self.default_site_concurrency = default_site_concurrency
        self.site_concurrency_overrides = site_concurrency_overrides or {}
        self.task_type_limits = task_type_limits or {}


class _FakeSettings:
    def __init__(self, crawl: _FakeCrawlSettings):
        self.crawl = crawl


def test_from_settings_reads_dict_typed_limits():
    fake_settings = _FakeSettings(
        _FakeCrawlSettings(
            default_site_concurrency=2,
            site_concurrency_overrides={'javdb': 4, 'youtube': 1},
            task_type_limits={
                'subscription_sync_incremental': 2,
                'subscription_sync_full': 1,
                'video_extract': 8,
            },
        )
    )

    with patch('domains.subscription.application.services.crawl.dispatcher.policy.settings', fake_settings):
        policy = CrawlDispatcherPolicy.from_settings()

    assert policy.default_site_concurrency == 2
    assert policy.get_site_limit('javdb') == 4
    assert policy.get_site_limit('youtube') == 1
    assert policy.get_site_limit('unknown') == 2  # falls back to default
    assert policy.get_task_type_limit('video_extract') == 8
    assert policy.get_task_type_limit('subscription_sync_full') == 1
    assert policy.get_task_type_limit('missing') is None


def test_from_settings_returns_independent_copies():
    """Mutating the returned policy must not leak back into CrawlSettings."""
    src_overrides = {'javdb': 4}
    src_limits = {'video_extract': 8}
    fake_settings = _FakeSettings(
        _FakeCrawlSettings(
            default_site_concurrency=2,
            site_concurrency_overrides=src_overrides,
            task_type_limits=src_limits,
        )
    )

    with patch('domains.subscription.application.services.crawl.dispatcher.policy.settings', fake_settings):
        policy = CrawlDispatcherPolicy.from_settings()

    policy.site_concurrency_overrides['javdb'] = 99
    policy.task_type_limits['video_extract'] = 99
    assert src_overrides['javdb'] == 4
    assert src_limits['video_extract'] == 8


def test_is_site_available_respects_overrides():
    policy = CrawlDispatcherPolicy(
        default_site_concurrency=2,
        site_concurrency_overrides={'javdb': 1},
    )
    assert policy.is_site_available('javdb', running_count=0) is True
    assert policy.is_site_available('javdb', running_count=1) is False
    assert policy.is_site_available('youtube', running_count=1) is True
    assert policy.is_site_available('youtube', running_count=2) is False
