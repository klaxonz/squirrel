from datetime import datetime
from types import SimpleNamespace

from models.crawl_task import CrawlTask
from services import sync_center_stream_service
from services.subscription_sync_event_service import SubscriptionSyncEventService
from services.sync_center_stream_service import SyncCenterStreamService


def test_encode_sse_event_uses_named_event_with_json_payload():
    payload = {"overview": {"running_count": 1}}

    encoded = SyncCenterStreamService.encode_sse_event("feed_snapshot", payload)

    assert encoded == 'event: feed_snapshot\ndata: {"overview": {"running_count": 1}}\n\n'


def test_append_event_publishes_feed_and_run_invalidations(monkeypatch):
    sses_svc = SubscriptionSyncEventService()
    published = []

    stream_svc = sses_svc.stream_service
    stream_svc.SYNC_CENTER_FEED_CHANNEL = sync_center_stream_service.SYNC_CENTER_FEED_CHANNEL
    stream_svc.SYNC_CENTER_RUN_CHANNEL = sync_center_stream_service.SYNC_CENTER_RUN_CHANNEL
    monkeypatch.setattr(
        stream_svc,
        "publish_sync_center_invalidation",
        lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(
        sses_svc.projection_service,
        "apply_event",
        lambda event, session=None: None,
    )
    monkeypatch.setattr(
        sses_svc.run_service,
        "next_seq_no",
        lambda stream_id, session=None: 1,
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
    assert (sync_center_stream_service.SYNC_CENTER_FEED_CHANNEL, None) in published
    assert (sync_center_stream_service.SYNC_CENTER_RUN_CHANNEL, {"run_id": "run-9"}) in published


def test_refresh_projection_for_task_publishes_extract_invalidations(monkeypatch):
    from services.video_extraction_projection_service import VideoExtractionProjectionService
    svc = VideoExtractionProjectionService()
    published = []

    monkeypatch.setattr(
        svc,
        "_get_publish_sync_center_invalidation",
        lambda: lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(
        svc,
        "_get_sync_center_extract_channel",
        lambda: sync_center_stream_service.SYNC_CENTER_EXTRACT_CHANNEL,
    )
    monkeypatch.setattr(svc, "_refresh_projection_group", lambda *args, **kwargs: None)

    task = CrawlTask(
        job_id=1,
        task_type="video_extract",
        site="youtube",
        subscription_id=9,
        payload={"run_id": "run-9"},
    )
    svc.refresh_projection_for_task(task, session=object())

    assert (sync_center_stream_service.SYNC_CENTER_EXTRACT_CHANNEL, {"run_id": "run-9"}) in published
