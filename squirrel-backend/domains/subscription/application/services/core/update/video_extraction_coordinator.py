import logging

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
import domains.video.application.services.extraction.task_service as video_extraction_task_service
from infrastructure.database.session import get_session
from infrastructure.observability.collector.instance import metrics
from infrastructure.site_catalog.url import resolve_site
from domains.subscription.application.services.core.runtime_models import SubscriptionSyncResult
from domains.subscription.application.services.core.sync.event_service import SyncEventInput, append_event
from domains.subscription.application.services.core.sync.run_service import SyncEventType, SyncRunStatus
from domains.video.interfaces.dto.dto.video_dto import VideoExtractDto
from domains.video.application.services.crud import get_videos_by_urls
from domains.video.application.services.extraction.extractor import extract_video
from domains.video.application.services.moderation.blocked import is_blocked_video

from .models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger

logger = logging.getLogger(__name__)


class VideoExtractionCoordinator:
    def enqueue_discovered_videos(
        self,
        fetch_result: SubscriptionSyncResult,
        request: SubscriptionUpdateRequest,
    ) -> int:
        enqueued = 0
        existing_count = 0
        failed_count = 0
        blocked_count = 0
        is_full_update = request.mode == UpdateMode.FULL
        video_urls = fetch_result.video_urls
        total = len(video_urls)
        existing_videos = get_videos_by_urls(video_urls)
        domain = resolve_site(request.url) or "unknown"

        blocked_video_urls = set()
        with get_session() as session:
            for video_url in video_urls:
                if is_blocked_video(video_url, session):
                    blocked_video_urls.add(video_url)

        for video_url in video_urls:
            existing_video = existing_videos.get(video_url)
            if existing_video:
                existing_count += 1
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_in_db"})
                continue
            if video_url in blocked_video_urls:
                blocked_count += 1
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "blocked_video"})
                continue

            reserved_pending = False
            try:
                params = VideoExtractDto(
                    url=video_url,
                    subscribed=True,
                    only_extract=True,
                    subscription_id=request.subscription_id,
                    sync_state_id=request.sync_state_id,
                    run_id=request.run_id,
                    trigger=request.trigger.value,
                    is_manual=request.trigger == UpdateTrigger.MANUAL,
                    is_extract_all=is_full_update,
                )
                subscription_sync_state_service.increment_pending_video_count(request.sync_state_id, 1)
                reserved_pending = True
                if request.inline_video_extraction:
                    extracted = extract_video(params)
                    if extracted.success:
                        enqueued += 1
                    else:
                        failed_count += 1
                        logger.warning("Failed to extract video %s: %s", video_url, extracted.error)
                elif video_extraction_task_service.enqueue_video_extraction(params):
                    enqueued += 1
                else:
                    subscription_sync_state_service.decrement_pending_video_count(
                        request.sync_state_id,
                        allow_completion=False,
                    )
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                if reserved_pending:
                    subscription_sync_state_service.decrement_pending_video_count(
                        request.sync_state_id,
                        allow_completion=False,
                    )
                failed_count += 1
                logger.warning("Failed to enqueue video %s: %s", video_url, exc)

        self._append_run_events(
            request=request,
            domain=domain,
            total=total,
            enqueued=enqueued,
            skipped=existing_count + blocked_count,
        )

        logger.debug(
            "Enqueue summary subscription_id=%s domain=%s trigger=%s mode=%s total=%s queued=%s existed=%s blocked=%s failed=%s",
            request.subscription_id,
            domain,
            request.trigger.value,
            request.mode.value,
            total,
            enqueued,
            existing_count,
            blocked_count,
            failed_count,
        )
        return enqueued

    @staticmethod
    def _append_run_events(
        *,
        request: SubscriptionUpdateRequest,
        domain: str,
        total: int,
        enqueued: int,
        skipped: int,
    ) -> None:
        if not request.run_id:
            return

        append_event(
            SyncEventInput(
                stream_id=request.run_id,
                subscription_id=request.subscription_id,
                sync_state_id=request.sync_state_id,
                site=domain,
                sync_mode=request.mode.value,
                trigger=request.trigger.value,
                request_id=request.request_id,
                trace_id=request.trace_id,
                event_type=SyncEventType.VIDEO_FOUND,
                event_phase="calculating_delta",
                event_status=SyncRunStatus.RUNNING,
                payload={"videos_found_delta": total, "videos_found": total},
            ),
        )
        append_event(
            SyncEventInput(
                stream_id=request.run_id,
                subscription_id=request.subscription_id,
                sync_state_id=request.sync_state_id,
                site=domain,
                sync_mode=request.mode.value,
                trigger=request.trigger.value,
                request_id=request.request_id,
                trace_id=request.trace_id,
                event_type=SyncEventType.VIDEO_ENQUEUED,
                event_phase="enqueueing",
                event_status=SyncRunStatus.RUNNING,
                payload={"videos_enqueued_delta": enqueued, "videos_enqueued": enqueued},
            ),
        )
        if skipped > 0:
            append_event(
                SyncEventInput(
                    stream_id=request.run_id,
                    subscription_id=request.subscription_id,
                    sync_state_id=request.sync_state_id,
                    site=domain,
                    sync_mode=request.mode.value,
                    trigger=request.trigger.value,
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    event_type=SyncEventType.VIDEO_SKIPPED,
                    event_phase="enqueueing",
                    event_status=SyncRunStatus.RUNNING,
                    payload={"videos_skipped_delta": skipped, "videos_skipped": skipped},
                ),
            )


video_extraction_coordinator = VideoExtractionCoordinator()
enqueue_discovered_videos = video_extraction_coordinator.enqueue_discovered_videos
