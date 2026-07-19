import logging

import domains.video.application.services.extraction.task_service as video_extraction_task_service
from domains.subscription.application.services.core.runtime_models import SubscriptionSyncResult
from domains.subscription.application.services.core.sync.lifecycle import subscription_sync_lifecycle
from domains.subscription.application.services.crawl.tasks.errors import CrawlExecutionError
from domains.video.application.services.crud import get_videos_by_urls
from domains.video.application.services.extraction.extractor import extract_video
from domains.video.application.services.extraction.video_persistence import video_persistence_service
from domains.video.application.services.moderation.blocked import is_blocked_video
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from infrastructure.database.session import get_session
from infrastructure.site_catalog.url import resolve_site

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
        inline_failures = []
        dispatch_failures: list[Exception] = []
        blocked_count = 0
        is_full_update = request.mode == UpdateMode.FULL
        video_urls = fetch_result.video_urls
        total = len(video_urls)
        existing_videos = get_videos_by_urls(video_urls)
        domain = resolve_site(request.url) or 'unknown'

        blocked_video_urls = set()
        with get_session() as session:
            for video_url in video_urls:
                if is_blocked_video(video_url, session):
                    blocked_video_urls.add(video_url)

        link_kwargs = {}
        if request.sync_state_id is not None or request.run_id is not None or request.execution_token is not None:
            link_kwargs = {
                'sync_state_id': request.sync_state_id,
                'run_id': request.run_id,
                'execution_token': request.execution_token,
            }
        video_persistence_service.link_existing_videos(
            request.subscription_id,
            [video.id for video_url, video in existing_videos.items() if video_url not in blocked_video_urls],
            **link_kwargs,
        )

        for video_url in video_urls:
            if video_url in blocked_video_urls:
                blocked_count += 1
                continue
            existing_video = existing_videos.get(video_url)
            if existing_video:
                existing_count += 1
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
                    parent_execution_token=request.execution_token,
                    execution_token=request.execution_token if request.inline_video_extraction else None,
                    trigger=request.trigger.value,
                    is_manual=request.trigger == UpdateTrigger.MANUAL,
                    is_extract_all=is_full_update,
                )
                if request.inline_video_extraction:
                    progress_kwargs = {'run_id': request.run_id}
                    if request.execution_token is not None:
                        progress_kwargs['execution_token'] = request.execution_token
                    subscription_sync_lifecycle.record_video_extraction_enqueued(
                        request.sync_state_id,
                        **progress_kwargs,
                    )
                    reserved_pending = True
                    extracted = extract_video(params)
                    if extracted.success:
                        enqueued += 1
                    else:
                        failed_count += 1
                        inline_failures.append(extracted)
                        logger.warning('Failed to extract video %s: %s', video_url, extracted.error)
                    terminal_kwargs = {
                        'succeeded': bool(extracted.success),
                        'run_id': request.run_id,
                    }
                    if request.execution_token is not None:
                        terminal_kwargs['execution_token'] = request.execution_token
                    subscription_sync_lifecycle.record_video_extraction_terminal(
                        request.sync_state_id,
                        **terminal_kwargs,
                    )
                    reserved_pending = False
                elif video_extraction_task_service.enqueue_video_extraction(params):
                    enqueued += 1
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                failed_count += 1
                dispatch_failures.append(exc)
                logger.warning('Failed to enqueue video %s: %s', video_url, exc)
            finally:
                if reserved_pending:
                    cleanup_kwargs = {'run_id': request.run_id}
                    if request.execution_token is not None:
                        cleanup_kwargs['execution_token'] = request.execution_token
                    subscription_sync_lifecycle.record_video_extraction_dispatch_failed(
                        request.sync_state_id,
                        **cleanup_kwargs,
                    )

        logger.debug(
            'Enqueue summary subscription_id=%s domain=%s trigger=%s mode=%s total=%s queued=%s existed=%s blocked=%s failed=%s',
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
        if inline_failures:
            first_failure = inline_failures[0]
            raise CrawlExecutionError(
                f'{len(inline_failures)} inline video extraction(s) failed; first error: '
                f"{getattr(first_failure, 'error', None) or 'unknown'}",
                retryable=any(bool(getattr(item, 'retryable', False)) for item in inline_failures),
                error_type=str(
                    getattr(first_failure, 'error_category', None) or 'inline_video_extraction_failed',
                ),
            )
        if dispatch_failures:
            first_failure = dispatch_failures[0]
            raise CrawlExecutionError(
                f'{len(dispatch_failures)} video extraction dispatch(es) failed; first error: {first_failure}',
                retryable=bool(getattr(first_failure, 'retryable', False)),
                error_type=str(getattr(first_failure, 'error_type', None) or type(first_failure).__name__),
            )
        return enqueued


video_extraction_coordinator = VideoExtractionCoordinator()
enqueue_discovered_videos = video_extraction_coordinator.enqueue_discovered_videos
