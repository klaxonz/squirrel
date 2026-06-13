from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.application.services.core.sync.event_service import SubscriptionSyncEventService
from domains.subscription.application.services.sync import stream_service as sync_dashboard_stream_service
from domains.subscription.application.services.sync.stream_service import SyncDashboardStreamService


def test_encode_sse_event_uses_named_event_with_json_payload():
    payload = {"overview": {"running_count": 1}}

    encoded = SyncDashboardStreamService.encode_sse_event("feed_snapshot", payload)

    assert encoded == 'event: feed_snapshot\ndata: {"overview": {"running_count": 1}}\n\n'


def test_append_event_publishes_feed_and_run_invalidations():
    published = []
    mock_projection = SimpleNamespace(apply_event=lambda event, session=None: None)
    mock_run = SimpleNamespace(next_seq_no=lambda stream_id, session=None: 1)
    mock_stream = SimpleNamespace(
        publish_sync_dashboard_invalidation=lambda channel, payload=None: published.append((channel, payload)),
        SYNC_DASHBOARD_FEED_CHANNEL=sync_dashboard_stream_service.SYNC_DASHBOARD_FEED_CHANNEL,
        SYNC_DASHBOARD_RUN_CHANNEL=sync_dashboard_stream_service.SYNC_DASHBOARD_RUN_CHANNEL,
    )

    sses_svc = SubscriptionSyncEventService(
        session_factory=lambda: SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *a: None),
        projection_service=mock_projection,
        run_service=mock_run,
        stream_service=mock_stream,
    )

    event = sses_svc.append_event(
        SimpleNamespace(
            stream_id="run-9",
            subscription_id=9,
            sync_mode="incremental",
            event_type="phase_changed",
            occurred_at=datetime(2026, 4, 5, 12, 0, 0),
            seq_no=None,
            sync_state_id=None,
            site=None,
            trigger=None,
            request_id=None,
            trace_id=None,
            event_phase=None,
            event_status=None,
            payload=None,
            message=None,
        ),
        session=SimpleNamespace(add=lambda event: None, flush=lambda: None),
    )

    assert event.stream_id == "run-9"
    assert (sync_dashboard_stream_service.SYNC_DASHBOARD_FEED_CHANNEL, None) in published
    assert (sync_dashboard_stream_service.SYNC_DASHBOARD_RUN_CHANNEL, {"run_id": "run-9"}) in published


def test_append_event_uses_module_channels_with_default_shaped_stream_service():
    published = []
    mock_projection = SimpleNamespace(apply_event=lambda event, session=None: None)
    mock_run = SimpleNamespace(next_seq_no=lambda stream_id, session=None: 1)
    mock_stream = SimpleNamespace(
        publish_sync_dashboard_invalidation=lambda channel, payload=None: published.append((channel, payload)),
    )

    sses_svc = SubscriptionSyncEventService(
        session_factory=lambda: SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *a: None),
        projection_service=mock_projection,
        run_service=mock_run,
        stream_service=mock_stream,
    )

    sses_svc.append_event(
        SimpleNamespace(
            stream_id="run-10",
            subscription_id=10,
            sync_mode="incremental",
            event_type="queued",
            occurred_at=datetime(2026, 4, 5, 12, 1, 0),
            seq_no=None,
            sync_state_id=None,
            site=None,
            trigger=None,
            request_id=None,
            trace_id=None,
            event_phase=None,
            event_status=None,
            payload=None,
            message=None,
        ),
        session=SimpleNamespace(add=lambda event: None, flush=lambda: None),
    )

    assert (sync_dashboard_stream_service.SYNC_DASHBOARD_FEED_CHANNEL, None) in published
    assert (sync_dashboard_stream_service.SYNC_DASHBOARD_RUN_CHANNEL, {"run_id": "run-10"}) in published


def test_refresh_projection_for_task_publishes_extract_invalidations():
    import video.services.extraction_projection.store as projection_store
    from domains.video.application.services.extraction_projection.service import VideoExtractionProjectionService

    published = []
    svc = VideoExtractionProjectionService(
        publish_sync_dashboard_invalidation=lambda channel, payload=None: published.append((channel, payload)),
        sync_dashboard_extract_channel=sync_dashboard_stream_service.SYNC_DASHBOARD_EXTRACT_CHANNEL,
    )

    with patch.object(projection_store, 'refresh_projection_group'):
        task = CrawlTask(
            job_id=1,
            task_type="video_extract",
            site="youtube",
            subscription_id=9,
            payload={"run_id": "run-9"},
        )
        svc.refresh_projection_for_task(task, session=object())

    assert (sync_dashboard_stream_service.SYNC_DASHBOARD_EXTRACT_CHANNEL, {"run_id": "run-9"}) in published
