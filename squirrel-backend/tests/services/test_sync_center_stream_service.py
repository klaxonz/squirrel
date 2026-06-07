import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.crawl_task import CrawlTask
from services import subscription_sync_event_service, sync_center_stream_service, video_extraction_projection_service


def test_encode_sse_event_uses_named_event_with_json_payload():
    payload = {"overview": {"running_count": 1}}

    encoded = sync_center_stream_service.encode_sse_event("feed_snapshot", payload)

    assert encoded == 'event: feed_snapshot\ndata: {"overview": {"running_count": 1}}\n\n'


def test_append_event_publishes_feed_and_run_invalidations(monkeypatch):
    published = []

    monkeypatch.setattr(
        sync_center_stream_service,
        "publish_sync_center_invalidation",
        lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(
        subscription_sync_event_service.subscription_sync_projection_service,
        "apply_event",
        lambda event, session=None: None,
    )
    monkeypatch.setattr(
        subscription_sync_event_service.subscription_sync_run_service,
        "next_seq_no",
        lambda stream_id, session=None: 1,
    )

    event = subscription_sync_event_service.append_event(
        subscription_sync_event_service.SyncEventInput(
            stream_id="run-9",
            subscription_id=9,
            sync_mode="incremental",
            event_type="phase_changed",
            occurred_at=datetime(2026, 4, 5, 12, 0, 0),
        ),
        session=SimpleNamespace(add=lambda event: None, flush=lambda: None),
    )

    assert event.stream_id == "run-9"
    assert (sync_center_stream_service.SYNC_CENTER_FEED_CHANNEL, None) in published
    assert (sync_center_stream_service.SYNC_CENTER_RUN_CHANNEL, {"run_id": "run-9"}) in published


def test_refresh_projection_for_task_publishes_extract_invalidations(monkeypatch):
    published = []

    monkeypatch.setattr(
        sync_center_stream_service,
        "publish_sync_center_invalidation",
        lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(video_extraction_projection_service, "_refresh_projection_group", lambda *args, **kwargs: None)

    task = CrawlTask(
        job_id=1,
        task_type="video_extract",
        site="youtube",
        subscription_id=9,
        payload={"run_id": "run-9"},
    )
    video_extraction_projection_service.refresh_projection_for_task(task, session=object())

    assert (sync_center_stream_service.SYNC_CENTER_EXTRACT_CHANNEL, {"run_id": "run-9"}) in published
