"""
默认更新策略（适用于所有站点）
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import update
from core.config import settings
from core.database import get_session
from urllib.parse import urlparse
from models.subscription import Subscription as SubscriptionModel
from models.subscription_sync_state import SyncMode, SyncStatus
from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.ports import get_runtime_gateway
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_service, subscription_sync_state_service, video_service
from services.blocked_video_service import is_blocked_video
from services.subscription_runtime_models import SubscriptionSyncResult
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncRunStatus
from services.video_extraction import extract_video
from utils.site_catalog import SiteCatalog
from utils.metrics import metrics
from .base import UpdateStrategy
from ..models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode, UpdateTrigger

logger = logging.getLogger(__name__)

FULL_BACKFILL_RETRY_COOLDOWN = timedelta(hours=6)
FULL_BACKFILL_STALE_AFTER = timedelta(days=3)


def should_schedule_total_video_backfill(
    sync_mode: str,
    local_total_videos: Optional[int],
    observed_total_available: Optional[int],
    full_sync_status: Optional[str],
    full_last_success_at: Optional[datetime],
    *,
    now: Optional[datetime] = None,
) -> bool:
    current_time = now or datetime.now()

    if sync_mode == SyncMode.FULL.value:
        return False
    if full_sync_status in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
        return False

    local_total = max(int(local_total_videos or 0), 0)
    observed_total = max(int(observed_total_available), 0) if observed_total_available is not None else None

    if full_last_success_at is None:
        return True

    if local_total <= 0 and full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN:
        return True

    if observed_total is not None and observed_total > local_total:
        return full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN

    return full_last_success_at <= current_time - FULL_BACKFILL_STALE_AFTER


class DefaultUpdateStrategy(UpdateStrategy):
    """默认更新策略（适用于所有站点）"""

    def __init__(self, runtime_gateway: SiteRuntimeGateway | None = None) -> None:
        self._runtime_gateway = runtime_gateway

    @property
    def site_name(self) -> str:
        return "default"

    def execute(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        result = super().execute(request)
        if result.success:
            self._record_gap_observation(request, result)
            self._schedule_total_video_backfill(request, result)
        return result
    
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, Optional[str]]:
        """检查是否需要更新"""
        sub = subscription_service.get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, "subscription_not_found"
        return True, None
    
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> SubscriptionSyncResult:
        """获取视频列表"""
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc.lower().split(':')[0]
        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            raise ValueError(f'No subscription route found for domain: {domain}')

        sync_mode = UpdateMode.FULL if request.mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        runtime_gateway = self._runtime_gateway or get_runtime_gateway()
        response = runtime_gateway.invoke(
            'sync_subscription',
            site_name=site_name,
            domain=domain,
            payload={
                'url': request.url,
                'mode': sync_mode.value,
                'cursor_payload': request.cursor_payload or {},
                'last_seen_video_url': request.last_seen_video_url,
                'limit': None if sync_mode == UpdateMode.FULL else settings.CHANNEL_UPDATE_DEFAULT_SIZE,
            },
        )
        if not response.ok:
            message = response.error.message if response.error else f'Subscription sync failed for domain: {domain}'
            raise ValueError(message)
        if not isinstance(response.data, dict):
            raise ValueError(f'Subscription sync payload must be an object for domain: {domain}')

        result = SubscriptionSyncResult.from_dict(response.data)

        if sync_mode == UpdateMode.FULL and result.total_available is not None:
            self._update_total_videos(request.subscription_id, result.total_available)

        return result
    
    def enqueue_extraction(self, fetch_result: SubscriptionSyncResult, request: SubscriptionUpdateRequest) -> int:
        """将视频加入提取队列"""
        enqueued = 0
        existing_count = 0
        failed_count = 0
        blocked_count = 0
        is_full_update = request.mode == UpdateMode.FULL
        video_urls = fetch_result.video_urls
        total = len(fetch_result.video_urls)
        existing_videos = video_service.get_videos_by_urls(video_urls)

        # 获取站点信息用于指标
        domain = subscription_sync_state_service._resolve_site(request.url) or "unknown"

        # Batch check blocked videos to avoid repeated unsupported extractions.
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
            elif video_url in blocked_video_urls:
                blocked_count += 1
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "blocked_video"})
            else:
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
                        is_extract_all=is_full_update
                    )
                    subscription_sync_state_service.increment_pending_video_count(request.sync_state_id, 1)
                    reserved_pending = True
                    if request.inline_video_extraction:
                        result = extract_video(params)
                        if result.success:
                            enqueued += 1
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to extract video {video_url}: {result.error}")
                    elif download_service.enqueue_video_extraction(params):
                        enqueued += 1
                    else:
                        subscription_sync_state_service.decrement_pending_video_count(
                            request.sync_state_id,
                            allow_completion=False,
                        )
                except Exception as e:
                    if reserved_pending:
                        subscription_sync_state_service.decrement_pending_video_count(
                            request.sync_state_id,
                            allow_completion=False,
                        )
                    failed_count += 1
                    logger.warning(f"Failed to enqueue video {video_url}: {e}")

        if request.run_id:
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
                    event_phase='calculating_delta',
                    event_status=SyncRunStatus.RUNNING,
                    payload={'videos_found_delta': total, 'videos_found': total},
                )
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
                    event_phase='enqueueing',
                    event_status=SyncRunStatus.RUNNING,
                    payload={'videos_enqueued_delta': enqueued, 'videos_enqueued': enqueued},
                )
            )
            skipped_total = existing_count + blocked_count
            if skipped_total > 0:
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
                        event_phase='enqueueing',
                        event_status=SyncRunStatus.RUNNING,
                        payload={'videos_skipped_delta': skipped_total, 'videos_skipped': skipped_total},
                    )
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
    def _update_total_videos(subscription_id: int, total: int) -> None:
        """更新订阅总视频数"""
        with get_session() as session:
            session.execute(
                update(SubscriptionModel)
                .where(SubscriptionModel.id == subscription_id)
                .values(total_videos=total)
            )

    @staticmethod
    def _schedule_total_video_backfill(
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> None:
        if request.inline_video_extraction:
            return

        subscription = subscription_service.get_subscription_by_id(request.subscription_id)
        if not subscription:
            return

        full_state = subscription_sync_state_service.get_sync_state(request.subscription_id, SyncMode.FULL.value)
        if not should_schedule_total_video_backfill(
            request.mode.value,
            subscription.total_videos,
            result.total_available,
            full_state.sync_status if full_state else None,
            full_state.last_success_at if full_state else None,
        ):
            return

        from services.subscription_update import scheduler

        result = scheduler.schedule_one(
            subscription_id=request.subscription_id,
            url=request.url,
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.FULL,
            trace_id=request.trace_id,
        )
        logger.info(
            "Scheduled full sync to backfill total videos: subscription_id=%s, status=%s",
            request.subscription_id,
            result.status,
        )

    @staticmethod
    def _record_gap_observation(request: SubscriptionUpdateRequest, result: SubscriptionUpdateResult) -> None:
        if request.mode != UpdateMode.INCREMENTAL or not request.sync_state_id:
            return

        subscription = subscription_service.get_subscription_by_id(request.subscription_id)
        local_total = getattr(subscription, 'total_videos', None) if subscription else None
        subscription_sync_state_service.record_gap_observation(
            sync_state_id=request.sync_state_id,
            head_sample_urls=result.head_sample_urls,
            anchor_found=result.anchor_found,
            cursor_invalid=bool(result.cursor_invalid),
            cursor_loop_detected=bool(result.cursor_loop_detected),
            total_available=result.total_available,
            local_total=local_total,
            trigger=request.trigger.value,
            trace_id=request.trace_id,
        )


