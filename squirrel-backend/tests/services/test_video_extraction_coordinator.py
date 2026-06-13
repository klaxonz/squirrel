from types import SimpleNamespace
from unittest.mock import patch

from services.subscription.update.models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger
from services.subscription.update.video_extraction_coordinator import VideoExtractionCoordinator


class _DummySessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_enqueue_discovered_videos_skips_blocked_video_urls():
    counter_calls = []
    enqueue_calls = []

    with patch("services.subscription.update.video_extraction_coordinator.get_videos_by_urls", return_value={}), \
         patch("services.subscription.update.video_extraction_coordinator.get_session", return_value=_DummySessionContext()), \
         patch("services.subscription.update.video_extraction_coordinator.is_blocked_video", side_effect=lambda url, session: url.endswith("blocked")), \
         patch("services.subscription.update.video_extraction_coordinator.video_extraction_task_service.enqueue_video_extraction", side_effect=lambda params: enqueue_calls.append(params.url) or True), \
         patch("services.subscription.update.video_extraction_coordinator.subscription_sync_state_service.increment_pending_video_count"), \
         patch("services.subscription.update.video_extraction_coordinator.metrics.counter", side_effect=lambda name, tags=None: counter_calls.append((name, tags or {}))):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://www.pornhub.com/model/demo",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
        )
        fetch_result = SimpleNamespace(video_urls=[
            "https://www.pornhub.com/view_video.php?viewkey=blocked",
            "https://www.pornhub.com/view_video.php?viewkey=normal",
        ])

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert enqueue_calls == ["https://www.pornhub.com/view_video.php?viewkey=normal"]
    assert ("crawl.tasks.total", {"site": "pornhub.com", "status": "skipped", "reason": "blocked_video"}) in counter_calls


def test_enqueue_discovered_videos_reserves_pending_count_before_dispatching_video_task():
    pending_counts = {2: 0}

    def _increment_pending(sync_state_id, count):
        pending_counts[sync_state_id] = pending_counts.get(sync_state_id, 0) + count

    def _decrement_pending(sync_state_id, count=1, **kwargs):
        pending_counts[sync_state_id] = max(0, pending_counts.get(sync_state_id, 0) - count)

    def _enqueue_video(params):
        _decrement_pending(params.sync_state_id)
        return True

    with patch("services.subscription.update.video_extraction_coordinator.get_videos_by_urls", return_value={}), \
         patch("services.subscription.update.video_extraction_coordinator.get_session", return_value=_DummySessionContext()), \
         patch("services.subscription.update.video_extraction_coordinator.is_blocked_video", return_value=False), \
         patch("services.subscription.update.video_extraction_coordinator.subscription_sync_state_service.increment_pending_video_count", side_effect=_increment_pending), \
         patch("services.subscription.update.video_extraction_coordinator.subscription_sync_state_service.decrement_pending_video_count", side_effect=_decrement_pending), \
         patch("services.subscription.update.video_extraction_coordinator.video_extraction_task_service.enqueue_video_extraction", side_effect=_enqueue_video), \
         patch("services.subscription.update.video_extraction_coordinator.metrics.counter"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://www.youtube.com/channel/demo",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
        )
        fetch_result = SimpleNamespace(
            video_urls=["https://www.youtube.com/watch?v=demo"],
            latest_video_url="https://www.youtube.com/watch?v=demo",
            source_video_count=1,
        )

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert pending_counts[2] == 0


def test_enqueue_discovered_videos_extracts_inline_without_creating_video_task():
    extract_calls = []

    with patch("services.subscription.update.video_extraction_coordinator.get_videos_by_urls", return_value={}), \
         patch("services.subscription.update.video_extraction_coordinator.get_session", return_value=_DummySessionContext()), \
         patch("services.subscription.update.video_extraction_coordinator.is_blocked_video", return_value=False), \
         patch("services.subscription.update.video_extraction_coordinator.subscription_sync_state_service.increment_pending_video_count"), \
         patch("services.subscription.update.video_extraction_coordinator.video_extraction_task_service.enqueue_video_extraction", side_effect=lambda params: (_ for _ in ()).throw(AssertionError("inline extraction should not enqueue video task"))), \
         patch("services.subscription.update.video_extraction_coordinator.extract_video", side_effect=lambda params: extract_calls.append(params) or SimpleNamespace(success=True)), \
         patch("services.subscription.update.video_extraction_coordinator.metrics.counter"):

        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url="https://www.youtube.com/channel/demo",
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            inline_video_extraction=True,
        )
        fetch_result = SimpleNamespace(video_urls=["https://www.youtube.com/watch?v=demo"])

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert len(extract_calls) == 1
    assert extract_calls[0].url == "https://www.youtube.com/watch?v=demo"
    assert extract_calls[0].is_manual is True
