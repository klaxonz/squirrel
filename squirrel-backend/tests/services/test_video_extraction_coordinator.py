from types import SimpleNamespace
from unittest.mock import patch

import pytest

from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.application.services.core.update.models import (
    SubscriptionUpdateRequest,
    UpdateMode,
    UpdateTrigger,
)
from domains.subscription.application.services.core.update.video_extraction_coordinator import (
    VideoExtractionCoordinator,
)
from domains.subscription.application.services.crawl.tasks.errors import CrawlExecutionError
from domains.video.application.services.crud import VideoCrudService
from domains.video.application.services.extraction.extractor import VideoExtractionService
from domains.video.application.services.extraction.task_service import VideoExtractionTaskService
from domains.video.application.services.extraction.video_persistence import VideoPersistenceService


class _DummySessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_enqueue_discovered_videos_skips_blocked_video_urls():
    enqueue_calls = []

    with (
        patch.object(VideoCrudService, 'get_videos_by_urls', return_value={}),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            side_effect=lambda url, session: url.endswith('blocked'),
        ),
        patch.object(
            VideoExtractionTaskService,
            'enqueue',
            side_effect=lambda params: enqueue_calls.append(params.url) or True,
        ),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_enqueued'),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url='https://www.youtube.com/model/demo',
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
        )
        fetch_result = SimpleNamespace(
            video_urls=[
                'https://www.youtube.com/view_video.php?viewkey=blocked',
                'https://www.youtube.com/view_video.php?viewkey=normal',
            ]
        )

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert enqueue_calls == ['https://www.youtube.com/view_video.php?viewkey=normal']


def test_existing_blocked_video_is_not_linked_to_subscription():
    blocked_url = 'https://www.youtube.com/watch?v=blocked'
    allowed_url = 'https://www.youtube.com/watch?v=allowed'
    link_calls = []
    with (
        patch.object(
            VideoCrudService,
            'get_videos_by_urls',
            return_value={
                blocked_url: SimpleNamespace(id=10),
                allowed_url: SimpleNamespace(id=11),
            },
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            side_effect=lambda url, session: url == blocked_url,
        ),
        patch.object(
            VideoPersistenceService,
            'link_existing_videos',
            side_effect=lambda subscription_id, video_ids: link_calls.append((subscription_id, video_ids)),
        ),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=7,
            url='https://www.youtube.com/channel/demo',
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
        )

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(
            SimpleNamespace(video_urls=[blocked_url, allowed_url]),
            request,
        )

    assert enqueued == 0
    assert link_calls == [(7, [11])]


def test_enqueue_discovered_videos_delegates_atomic_pending_reservation_to_task_service():
    pending_counts = {2: 0}

    def _record_enqueued(sync_state_id):
        pending_counts[sync_state_id] = pending_counts.get(sync_state_id, 0) + 1

    def _decrement_pending(sync_state_id, count=1, **kwargs):
        pending_counts[sync_state_id] = max(0, pending_counts.get(sync_state_id, 0) - count)

    def _enqueue_video(params):
        return True

    with (
        patch.object(VideoCrudService, 'get_videos_by_urls', return_value={}),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            return_value=False,
        ),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_enqueued', side_effect=_record_enqueued),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_dispatch_failed', side_effect=_decrement_pending),
        patch.object(VideoExtractionTaskService, 'enqueue', side_effect=_enqueue_video),
    ):
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

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert pending_counts[2] == 0


def test_enqueue_discovered_videos_extracts_inline_without_creating_video_task():
    extract_calls = []
    terminal_calls = []

    with (
        patch.object(VideoCrudService, 'get_videos_by_urls', return_value={}),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            return_value=False,
        ),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_enqueued'),
        patch.object(
            VideoExtractionTaskService,
            'enqueue',
            side_effect=lambda params: (_ for _ in ()).throw(
                AssertionError('inline extraction should not enqueue video task')
            ),
        ),
        patch.object(
            VideoExtractionService,
            'extract_video',
            side_effect=lambda params: extract_calls.append(params) or SimpleNamespace(success=True),
        ),
        patch.object(
            SubscriptionSyncLifecycle,
            'record_video_extraction_terminal',
            side_effect=lambda *args, **kwargs: terminal_calls.append((args, kwargs)),
        ),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            url='https://www.youtube.com/channel/demo',
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            inline_video_extraction=True,
        )
        fetch_result = SimpleNamespace(video_urls=['https://www.youtube.com/watch?v=demo'])

        enqueued = VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert enqueued == 1
    assert len(extract_calls) == 1
    assert extract_calls[0].url == 'https://www.youtube.com/watch?v=demo'
    assert extract_calls[0].is_manual is True
    assert terminal_calls == [((2,), {'succeeded': True, 'run_id': None})]


def test_enqueue_discovered_videos_surfaces_inline_extraction_failure():
    with (
        patch.object(VideoCrudService, 'get_videos_by_urls', return_value={}),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            return_value=False,
        ),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_enqueued'),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_terminal'),
        patch.object(
            VideoExtractionService,
            'extract_video',
            return_value=SimpleNamespace(
                success=False,
                error='upstream timeout',
                retryable=True,
                error_category='network',
            ),
        ),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            run_id='run-1',
            url='https://www.youtube.com/channel/demo',
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            inline_video_extraction=True,
        )
        fetch_result = SimpleNamespace(video_urls=['https://www.youtube.com/watch?v=demo'])

        with pytest.raises(CrawlExecutionError) as exc_info:
            VideoExtractionCoordinator().enqueue_discovered_videos(fetch_result, request)

    assert exc_info.value.retryable is True
    assert exc_info.value.error_type == 'network'


def test_inline_extraction_releases_pending_reservation_on_unexpected_exception():
    cleanup_calls = []
    with (
        patch.object(VideoCrudService, 'get_videos_by_urls', return_value={}),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.get_session',
            return_value=_DummySessionContext(),
        ),
        patch(
            'domains.subscription.application.services.core.update.video_extraction_coordinator.is_blocked_video',
            return_value=False,
        ),
        patch.object(SubscriptionSyncLifecycle, 'record_video_extraction_enqueued'),
        patch.object(
            SubscriptionSyncLifecycle,
            'record_video_extraction_dispatch_failed',
            side_effect=lambda *args, **kwargs: cleanup_calls.append((args, kwargs)),
        ),
        patch.object(VideoExtractionService, 'extract_video', side_effect=RuntimeError('unexpected')),
    ):
        request = SubscriptionUpdateRequest(
            subscription_id=1,
            sync_state_id=2,
            run_id='run-1',
            url='https://www.youtube.com/channel/demo',
            trigger=UpdateTrigger.MANUAL,
            mode=UpdateMode.INCREMENTAL,
            inline_video_extraction=True,
        )

        with pytest.raises(RuntimeError, match='unexpected'):
            VideoExtractionCoordinator().enqueue_discovered_videos(
                SimpleNamespace(video_urls=['https://www.youtube.com/watch?v=demo']),
                request,
            )

    assert cleanup_calls == [((2,), {'run_id': 'run-1'})]
