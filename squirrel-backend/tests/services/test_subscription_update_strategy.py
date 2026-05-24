from datetime import datetime, timedelta
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'squirrel-sdk' / 'src'))

from crawl import PluginInvokeResponse
from services.subscription_update.models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode, UpdateTrigger
from services.subscription_update.strategies.default_strategy import DefaultUpdateStrategy, should_schedule_total_video_backfill


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
        full_sync_status='queued',
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


def test_inline_video_extraction_does_not_schedule_total_video_backfill(monkeypatch):
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id',
        lambda subscription_id: (_ for _ in ()).throw(AssertionError('inline extraction should not schedule backfill')),
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://www.youtube.com/channel/demo',
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


def test_fetch_videos_uses_plugin_gateway_sync_subscription(monkeypatch):
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='sync-1',
                ok=True,
                data={
                    'video_urls': ['https://www.bilibili.com/video/BV1xx411c7mD'],
                    'latest_video_url': 'https://www.bilibili.com/video/BV1xx411c7mD',
                    'cursor_payload': {'latest_video_url': 'https://www.bilibili.com/video/BV1xx411c7mD'},
                    'stop_reason': 'source_exhausted',
                    'total_available': 1,
                },
            )

    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.SiteCatalog.find_site_by_domain',
        lambda domain: ('bilibili', {'domains': ['bilibili.com']}),
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
        cursor_payload={'cursor': '1'},
        last_seen_video_url='https://www.bilibili.com/video/OLD',
    )

    result = DefaultUpdateStrategy().fetch_videos(request)

    assert calls == [{
        'capability': 'sync_subscription',
        'payload': {
            'url': 'https://space.bilibili.com/42',
            'mode': 'incremental',
            'cursor_payload': {'cursor': '1'},
            'last_seen_video_url': 'https://www.bilibili.com/video/OLD',
            'limit': 30,
        },
        'site_name': 'bilibili',
        'domain': 'space.bilibili.com',
        'timeout_ms': None,
    }]
    assert result.video_urls == ['https://www.bilibili.com/video/BV1xx411c7mD']
    assert result.latest_video_url == 'https://www.bilibili.com/video/BV1xx411c7mD'
    assert result.total_available == 1


def test_enqueue_extraction_skips_blocked_video_urls(monkeypatch):
    counter_calls = []
    enqueue_calls = []

    class _DummySessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.video_service.get_videos_by_urls',
        lambda urls: {},
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.get_session',
        lambda: _DummySessionContext(),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.is_blocked_video',
        lambda url, session: url.endswith('blocked'),
        raising=False,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.download_service.enqueue_video_extraction',
        lambda params: enqueue_calls.append(params.url) or True,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.increment_pending_video_count',
        lambda sync_state_id, count: None,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.metrics.counter',
        lambda name, tags=None: counter_calls.append((name, tags or {})),
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://www.pornhub.com/model/demo',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
    )
    fetch_result = SimpleNamespace(video_urls=[
        'https://www.pornhub.com/view_video.php?viewkey=blocked',
        'https://www.pornhub.com/view_video.php?viewkey=normal',
    ])

    enqueued = DefaultUpdateStrategy().enqueue_extraction(fetch_result, request)

    assert enqueued == 1
    assert enqueue_calls == ['https://www.pornhub.com/view_video.php?viewkey=normal']
    assert ('crawl.tasks.total', {'site': 'pornhub.com', 'status': 'skipped', 'reason': 'blocked_video'}) in counter_calls


def test_enqueue_extraction_reserves_pending_count_before_dispatching_video_task(monkeypatch):
    pending_counts = {2: 0}

    class _DummySessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    def _increment_pending(sync_state_id, count):
        pending_counts[sync_state_id] = pending_counts.get(sync_state_id, 0) + count

    def _decrement_pending(sync_state_id, count=1):
        pending_counts[sync_state_id] = max(0, pending_counts.get(sync_state_id, 0) - count)

    def _enqueue_video(params):
        _decrement_pending(params.sync_state_id)
        return True

    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.video_service.get_videos_by_urls',
        lambda urls: {},
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.get_session',
        lambda: _DummySessionContext(),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.is_blocked_video',
        lambda url, session: False,
        raising=False,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.increment_pending_video_count',
        _increment_pending,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.decrement_pending_video_count',
        _decrement_pending,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.download_service.enqueue_video_extraction',
        _enqueue_video,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.metrics.counter',
        lambda *args, **kwargs: None,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
    )
    fetch_result = SimpleNamespace(
        video_urls=['https://www.youtube.com/watch?v=demo'],
        latest_video_url='https://www.youtube.com/watch?v=demo',
        source_video_count=1,
    )

    enqueued = DefaultUpdateStrategy().enqueue_extraction(fetch_result, request)

    assert enqueued == 1
    assert pending_counts[2] == 0


def test_enqueue_extraction_extracts_inline_without_creating_video_task(monkeypatch):
    extract_calls = []

    class _DummySessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.video_service.get_videos_by_urls',
        lambda urls: {},
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.get_session',
        lambda: _DummySessionContext(),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.is_blocked_video',
        lambda url, session: False,
        raising=False,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.increment_pending_video_count',
        lambda sync_state_id, count: None,
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.download_service.enqueue_video_extraction',
        lambda params: (_ for _ in ()).throw(AssertionError('inline extraction should not enqueue video task')),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.extract_video',
        lambda params: extract_calls.append(params) or SimpleNamespace(success=True),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.metrics.counter',
        lambda *args, **kwargs: None,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
        inline_video_extraction=True,
    )
    fetch_result = SimpleNamespace(video_urls=['https://www.youtube.com/watch?v=demo'])

    enqueued = DefaultUpdateStrategy().enqueue_extraction(fetch_result, request)

    assert enqueued == 1
    assert len(extract_calls) == 1
    assert extract_calls[0].url == 'https://www.youtube.com/watch?v=demo'
    assert extract_calls[0].is_manual is True


def test_execute_full_sync_with_more_batches_continues_without_marking_success(monkeypatch):
    continuation_calls = []
    success_calls = []
    schedule_calls = []

    monkeypatch.setattr(DefaultUpdateStrategy, '_schedule_total_video_backfill', staticmethod(lambda request, result: None))
    monkeypatch.setattr(DefaultUpdateStrategy, 'should_update', lambda self, request: (True, None))
    monkeypatch.setattr(
        DefaultUpdateStrategy,
        'fetch_videos',
        lambda self, request: SimpleNamespace(
            video_urls=['https://example.com/a', 'https://example.com/b'],
            latest_video_url='https://example.com/a',
            cursor_payload={'page': 2},
            source_video_count=2,
            total_available=2,
            has_more=True,
        ),
    )
    monkeypatch.setattr(DefaultUpdateStrategy, 'enqueue_extraction', lambda self, fetch_result, request: 2)
    monkeypatch.setattr(
        'services.subscription_update.strategies.base.subscription_sync_state_service.mark_sync_success',
        lambda sync_state_id, **kwargs: success_calls.append((sync_state_id, kwargs)),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.base.subscription_sync_state_service.continue_full_sync_batch',
        lambda sync_state_id, **kwargs: continuation_calls.append((sync_state_id, kwargs)),
        raising=False,
    )
    monkeypatch.setattr(
        'services.subscription_update.scheduler.schedule_one',
        lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status='queued', run_id=kwargs.get('run_id')),
    )
    monkeypatch.setattr('services.subscription_update.strategies.base.metrics.counter', lambda *args, **kwargs: None)
    monkeypatch.setattr('services.subscription_update.strategies.base.append_event', lambda *args, **kwargs: None)

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL,
        cursor_payload={'page': 1},
        run_id='run-1',
        request_id='req-1',
        trace_id='trace-1',
    )

    result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert result.cursor_payload == {'page': 2}
    assert success_calls == []
    assert continuation_calls == [
        (
            2,
            {
                'cursor_payload': {'page': 2},
                'latest_video_url': 'https://example.com/a',
                'source_video_count': 2,
                'videos_found': 2,
                'videos_enqueued': 2,
                'run_id': 'run-1',
                'request_id': 'req-1',
                'trace_id': 'trace-1',
                'trigger': 'manual',
            },
        )
    ]
    assert schedule_calls == [
        {
            'subscription_id': 1,
            'url': 'https://space.bilibili.com/42',
            'trigger': UpdateTrigger.MANUAL,
            'mode': UpdateMode.FULL,
            'user_id': None,
            'force': False,
            'trace_id': 'trace-1',
            'run_id': 'run-1',
        }
    ]


def test_execute_final_full_sync_batch_marks_success(monkeypatch):
    success_calls = []
    continuation_calls = []
    schedule_calls = []

    monkeypatch.setattr(DefaultUpdateStrategy, '_schedule_total_video_backfill', staticmethod(lambda request, result: None))
    monkeypatch.setattr(DefaultUpdateStrategy, 'should_update', lambda self, request: (True, None))
    monkeypatch.setattr(
        DefaultUpdateStrategy,
        'fetch_videos',
        lambda self, request: SimpleNamespace(
            video_urls=['https://example.com/c'],
            latest_video_url='https://example.com/c',
            cursor_payload={'page': 3},
            source_video_count=1,
            total_available=3,
            has_more=False,
        ),
    )
    monkeypatch.setattr(DefaultUpdateStrategy, 'enqueue_extraction', lambda self, fetch_result, request: 1)
    monkeypatch.setattr(
        'services.subscription_update.strategies.base.subscription_sync_state_service.mark_sync_success',
        lambda sync_state_id, **kwargs: success_calls.append((sync_state_id, kwargs)),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.base.subscription_sync_state_service.continue_full_sync_batch',
        lambda sync_state_id, **kwargs: continuation_calls.append((sync_state_id, kwargs)),
        raising=False,
    )
    monkeypatch.setattr(
        'services.subscription_update.scheduler.schedule_one',
        lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status='queued', run_id=kwargs.get('run_id')),
    )
    monkeypatch.setattr('services.subscription_update.strategies.base.metrics.counter', lambda *args, **kwargs: None)
    monkeypatch.setattr('services.subscription_update.strategies.base.append_event', lambda *args, **kwargs: None)

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        sync_state_id=2,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.FULL,
        cursor_payload={'page': 2},
        run_id='run-1',
        request_id='req-2',
        trace_id='trace-1',
    )

    result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert continuation_calls == []
    assert schedule_calls == []
    assert success_calls == [
        (
            2,
            {
                'cursor_payload': {'page': 3},
                'latest_video_url': 'https://example.com/c',
                'source_video_count': 1,
                'videos_found': 1,
                'videos_enqueued': 1,
                'run_id': 'run-1',
                'request_id': 'req-2',
                'trace_id': 'trace-1',
                'trigger': 'manual',
            },
        )
    ]


def test_execute_incremental_schedules_full_backfill_when_observed_total_grows(monkeypatch):
    schedule_calls = []

    monkeypatch.setattr(DefaultUpdateStrategy, 'should_update', lambda self, request: (True, None))
    monkeypatch.setattr(
        DefaultUpdateStrategy,
        'fetch_videos',
        lambda self, request: SimpleNamespace(
            video_urls=['https://example.com/new'],
            latest_video_url='https://example.com/new',
            cursor_payload={'cursor': 'next'},
            source_video_count=1,
            total_available=15,
            has_more=False,
        ),
    )
    monkeypatch.setattr(DefaultUpdateStrategy, 'enqueue_extraction', lambda self, fetch_result, request: 1)
    monkeypatch.setattr(DefaultUpdateStrategy, '_record_gap_observation', staticmethod(lambda request, result: None))
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id',
        lambda subscription_id: SimpleNamespace(total_videos=10),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.get_sync_state',
        lambda subscription_id, mode: SimpleNamespace(
            sync_status='success',
            last_success_at=datetime(2026, 4, 8, 10, 0, 0),
        ),
    )
    monkeypatch.setattr(
        'services.subscription_update.scheduler.schedule_one',
        lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status='queued'),
    )
    monkeypatch.setattr('services.subscription_update.strategies.base.metrics.counter', lambda *args, **kwargs: None)

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-1',
    )

    result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert schedule_calls == [
        {
            'subscription_id': 1,
            'url': 'https://space.bilibili.com/42',
            'trigger': UpdateTrigger.SCHEDULED,
            'mode': UpdateMode.FULL,
            'trace_id': 'trace-1',
        }
    ]


def test_execute_incremental_does_not_schedule_full_backfill_when_full_already_running(monkeypatch):
    schedule_calls = []

    monkeypatch.setattr(DefaultUpdateStrategy, 'should_update', lambda self, request: (True, None))
    monkeypatch.setattr(
        DefaultUpdateStrategy,
        'fetch_videos',
        lambda self, request: SimpleNamespace(
            video_urls=['https://example.com/new'],
            latest_video_url='https://example.com/new',
            cursor_payload={'cursor': 'next'},
            source_video_count=1,
            total_available=15,
            has_more=False,
        ),
    )
    monkeypatch.setattr(DefaultUpdateStrategy, 'enqueue_extraction', lambda self, fetch_result, request: 1)
    monkeypatch.setattr(DefaultUpdateStrategy, '_record_gap_observation', staticmethod(lambda request, result: None))
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_service.get_subscription_by_id',
        lambda subscription_id: SimpleNamespace(total_videos=10),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.subscription_sync_state_service.get_sync_state',
        lambda subscription_id, mode: SimpleNamespace(
            sync_status='running',
            last_success_at=datetime(2026, 4, 8, 10, 0, 0),
        ),
    )
    monkeypatch.setattr(
        'services.subscription_update.scheduler.schedule_one',
        lambda **kwargs: schedule_calls.append(kwargs) or SimpleNamespace(status='queued'),
    )
    monkeypatch.setattr('services.subscription_update.strategies.base.metrics.counter', lambda *args, **kwargs: None)

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-1',
    )

    result = DefaultUpdateStrategy().execute(request)

    assert result.success is True
    assert schedule_calls == []
