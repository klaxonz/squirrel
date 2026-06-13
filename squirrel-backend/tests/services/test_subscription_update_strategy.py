from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from core.config import settings
from services.subscription_update import scheduler as _scheduler_instance
from services.subscription_update.models import (
    SubscriptionUpdateRequest,
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)
from services.subscription_update.strategies.default_strategy import (
    DefaultUpdateStrategy,
    should_schedule_total_video_backfill,
)


def test_should_schedule_total_video_backfill_when_full_never_succeeded():
    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=12,
        observed_total_available=None,
        full_sync_status=None,
        full_last_success_at=None,
    ) is True


def test_should_schedule_total_video_backfill_when_total_missing_after_cooldown():
    now = datetime(2026, 4, 9, 12, 0, 0)

    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=0,
        observed_total_available=None,
        full_sync_status=None,
        full_last_success_at=now - timedelta(hours=25),
        now=now,
    ) is True


def test_should_schedule_total_video_backfill_when_observed_total_drifts_after_cooldown():
    now = datetime(2026, 4, 9, 12, 0, 0)

    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=10,
        observed_total_available=15,
        full_sync_status=None,
        full_last_success_at=now - timedelta(hours=25),
        now=now,
    ) is True


def test_should_not_schedule_total_video_backfill_when_recent_full_is_still_cooling_down():
    now = datetime(2026, 4, 9, 12, 0, 0)

    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=10,
        observed_total_available=15,
        full_sync_status=None,
        full_last_success_at=now - timedelta(hours=1),
        now=now,
    ) is False


def test_should_not_schedule_total_video_backfill_when_full_is_already_queued():
    now = datetime(2026, 4, 9, 12, 0, 0)

    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=0,
        observed_total_available=None,
        full_sync_status="queued",
        full_last_success_at=now - timedelta(days=7),
        now=now,
    ) is False


def test_should_schedule_total_video_backfill_when_full_is_stale_even_without_observed_total():
    now = datetime(2026, 4, 9, 12, 0, 0)

    assert should_schedule_total_video_backfill(
        sync_mode=UpdateMode.INCREMENTAL.value,
        local_total_videos=10,
        observed_total_available=None,
        full_sync_status=None,
        full_last_success_at=now - timedelta(days=4),
        now=now,
    ) is True


def test_inline_video_extraction_does_not_schedule_total_video_backfill():
    with patch(
        "services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id",
        side_effect=lambda subscription_id: (_ for _ in ()).throw(AssertionError("inline extraction should not schedule backfill")),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://www.youtube.com/channel/demo",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            inline_video_extraction=True,
        )
        result = SubscriptionUpdateResult(
            subscription_id=1,
            success=True,
            videos_found=1,
            videos_enqueued=1,
            total_available=10,
        )

        DefaultUpdateStrategy._schedule_total_video_backfill(request, result)


def test_fetch_videos_uses_plugin_gateway_sync_subscription():
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                "capability": capability,
                "payload": payload,
                "site_name": site_name,
                "domain": domain,
                "timeout_ms": timeout_ms,
            })
            return SimpleNamespace(
                request_id="sync-1",
                ok=True,
                data={
                    "video_urls": ["https://www.bilibili.com/video/BV1xx411c7mD"],
                    "latest_video_url": "https://www.bilibili.com/video/BV1xx411c7mD",
                    "cursor_payload": {"latest_video_url": "https://www.bilibili.com/video/BV1xx411c7mD"},
                    "stop_reason": "source_exhausted",
                    "total_available": 1,
                },
            )

    with patch(
        "services.subscription_update.strategies.default_strategy.SiteCatalog.find_site_by_domain",
        return_value=("bilibili", {"domains": ["bilibili.com"]}),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            cursor_payload={"cursor": "1"},
            last_seen_video_url="https://www.bilibili.com/video/OLD",
        )

        result = DefaultUpdateStrategy(runtime_gateway=_FakeGateway()).fetch_videos(request)

    assert calls == [{
        "capability": "sync_subscription",
        "payload": {
            "url": "https://space.bilibili.com/42",
            "mode": "incremental",
            "cursor_payload": {"cursor": "1"},
            "last_seen_video_url": "https://www.bilibili.com/video/OLD",
            "limit": settings.CHANNEL_UPDATE_DEFAULT_SIZE,
        },
        "site_name": "bilibili",
        "domain": "space.bilibili.com",
        "timeout_ms": None,
    }]
    assert result.video_urls == ["https://www.bilibili.com/video/BV1xx411c7mD"]
    assert result.latest_video_url == "https://www.bilibili.com/video/BV1xx411c7mD"
    assert result.total_available == 1


def test_enqueue_extraction_delegates_to_video_extraction_coordinator():
    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url="https://www.youtube.com/channel/demo",
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
    )
    fetch_result = SimpleNamespace(video_urls=["https://www.youtube.com/watch?v=demo"])

    with patch(
        "services.subscription_update.strategies.default_strategy.enqueue_discovered_videos",
        return_value=1,
    ) as enqueue_discovered_videos:
        enqueued = DefaultUpdateStrategy().enqueue_extraction(fetch_result, request)

    assert enqueued == 1
    enqueue_discovered_videos.assert_called_once_with(fetch_result, request)


def test_execute_full_sync_with_more_batches_continues_without_marking_success():
    continuation_calls = []
    success_calls = []
    schedule_calls = []

    with patch.object(DefaultUpdateStrategy, "_schedule_total_video_backfill"), \
         patch.object(DefaultUpdateStrategy, "should_update", return_value=(True, None)), \
         patch.object(DefaultUpdateStrategy, "fetch_videos", return_value=SimpleNamespace(
             video_urls=["https://example.com/a", "https://example.com/b"],
             latest_video_url="https://example.com/a",
             cursor_payload={"page": 2},
             source_video_count=2,
             total_available=2,
             has_more=True,
         )), \
         patch.object(DefaultUpdateStrategy, "enqueue_extraction", return_value=2), \
         patch("services.subscription_update.strategies.base.subscription_sync_state_service.mark_sync_success", side_effect=lambda sync_state_id, **kwargs: success_calls.append((sync_state_id, kwargs))), \
         patch("services.subscription_update.strategies.base.subscription_sync_state_service.continue_full_sync_batch", side_effect=lambda sync_state_id, **kwargs: continuation_calls.append((sync_state_id, kwargs))), \
         patch.object(_scheduler_instance, "schedule_one", side_effect=lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status="queued", run_id=kwargs.get("run_id"))), \
         patch("services.subscription_update.strategies.base.metrics.counter"), \
         patch("services.subscription_update.strategies.base.append_event"), \
         patch("core.database.get_session"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.FULL,
            cursor_payload={"page": 1},
            run_id="run-1",
            request_id="req-1",
            trace_id="trace-1",
        )

        result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert result.cursor_payload == {"page": 2}
    assert success_calls == []
    assert continuation_calls == [
        (
            2,
            {
                "cursor_payload": {"page": 2},
                "latest_video_url": "https://example.com/a",
                "source_video_count": 2,
                "videos_found": 2,
                "videos_enqueued": 2,
                "run_id": "run-1",
                "request_id": "req-1",
                "trace_id": "trace-1",
                "trigger": "manual",
            },
        ),
    ]
    assert schedule_calls == [
        {
            "subscription_id": 1,
            "url": "https://space.bilibili.com/42",
            "trigger": UpdateTrigger.MANUAL,
            "mode": UpdateMode.FULL,
            "user_id": None,
            "force": False,
            "trace_id": "trace-1",
            "run_id": "run-1",
        },
    ]


def test_execute_final_full_sync_batch_marks_success():
    success_calls = []
    continuation_calls = []
    schedule_calls = []

    with patch.object(DefaultUpdateStrategy, "_schedule_total_video_backfill"), \
         patch.object(DefaultUpdateStrategy, "should_update", return_value=(True, None)), \
         patch.object(DefaultUpdateStrategy, "fetch_videos", return_value=SimpleNamespace(
             video_urls=["https://example.com/c"],
             latest_video_url="https://example.com/c",
             cursor_payload={"page": 3},
             source_video_count=1,
             total_available=3,
             has_more=False,
         )), \
         patch.object(DefaultUpdateStrategy, "enqueue_extraction", return_value=1), \
         patch("services.subscription_update.strategies.base.subscription_sync_state_service.mark_sync_success", side_effect=lambda sync_state_id, **kwargs: success_calls.append((sync_state_id, kwargs))), \
         patch("services.subscription_update.strategies.base.subscription_sync_state_service.continue_full_sync_batch", side_effect=lambda sync_state_id, **kwargs: continuation_calls.append((sync_state_id, kwargs))), \
         patch.object(_scheduler_instance, "schedule_one", side_effect=lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status="queued", run_id=kwargs.get("run_id"))), \
         patch("services.subscription_update.strategies.base.metrics.counter"), \
         patch("services.subscription_update.strategies.base.append_event"), \
         patch("core.database.get_session"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.FULL,
            cursor_payload={"page": 2},
            run_id="run-1",
            request_id="req-2",
            trace_id="trace-1",
        )

        result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert continuation_calls == []
    assert schedule_calls == []
    assert success_calls == [
        (
            2,
            {
                "cursor_payload": {"page": 3},
                "latest_video_url": "https://example.com/c",
                "source_video_count": 1,
                "videos_found": 1,
                "videos_enqueued": 1,
                "run_id": "run-1",
                "request_id": "req-2",
                "trace_id": "trace-1",
                "trigger": "manual",
            },
        ),
    ]


def test_execute_incremental_schedules_full_backfill_when_observed_total_grows():
    schedule_calls = []

    with patch.object(DefaultUpdateStrategy, "should_update", return_value=(True, None)), \
         patch.object(DefaultUpdateStrategy, "fetch_videos", return_value=SimpleNamespace(
             video_urls=["https://example.com/new"],
             latest_video_url="https://example.com/new",
             cursor_payload={"cursor": "next"},
             source_video_count=1,
             total_available=15,
             has_more=False,
         )), \
         patch.object(DefaultUpdateStrategy, "enqueue_extraction", return_value=1), \
         patch.object(DefaultUpdateStrategy, "_record_gap_observation"), \
         patch("services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id", return_value=SimpleNamespace(total_videos=10)), \
         patch("services.subscription_update.strategies.default_strategy.subscription_sync_state_service.get_sync_state", return_value=SimpleNamespace(
             sync_status="success",
             last_success_at=datetime(2026, 4, 8, 10, 0, 0),
         )), \
         patch.object(_scheduler_instance, "schedule_one", side_effect=lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status="queued")), \
         patch("services.subscription_update.strategies.base.metrics.counter"), \
         patch("services.subscription_update.strategies.base.append_event"), \
         patch("core.database.get_session"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
            trace_id="trace-1",
        )

        result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert schedule_calls == [
        {
            "subscription_id": 1,
            "url": "https://space.bilibili.com/42",
            "trigger": UpdateTrigger.SCHEDULED,
            "mode": UpdateMode.FULL,
            "trace_id": "trace-1",
        },
    ]


def test_execute_incremental_does_not_schedule_full_backfill_when_full_already_running():
    schedule_calls = []

    with patch.object(DefaultUpdateStrategy, "_schedule_total_video_backfill"), \
         patch.object(DefaultUpdateStrategy, "should_update", return_value=(True, None)), \
         patch.object(DefaultUpdateStrategy, "fetch_videos", return_value=SimpleNamespace(
             video_urls=["https://example.com/new"],
             latest_video_url="https://example.com/new",
             cursor_payload={"cursor": "next"},
             source_video_count=1,
             total_available=15,
             has_more=False,
         )), \
         patch.object(DefaultUpdateStrategy, "enqueue_extraction", return_value=1), \
         patch.object(DefaultUpdateStrategy, "_record_gap_observation"), \
         patch("services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id", return_value=SimpleNamespace(total_videos=10)), \
         patch("services.subscription_update.strategies.default_strategy.subscription_sync_state_service.get_sync_state", return_value=SimpleNamespace(
             sync_status="running",
             last_success_at=datetime(2026, 4, 8, 10, 0, 0),
         )), \
         patch.object(_scheduler_instance, "schedule_one", side_effect=lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status="queued")), \
         patch("services.subscription_update.strategies.base.metrics.counter"), \
         patch("services.subscription_update.strategies.base.append_event"), \
         patch("core.database.get_session"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            url="https://space.bilibili.com/42",
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
            trace_id="trace-1",
        )

        result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert schedule_calls == []
