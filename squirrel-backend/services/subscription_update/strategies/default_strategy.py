"""
默认更新策略（适用于所有站点）
"""
import logging
from typing import Optional

from sqlalchemy import update
from core.config import settings
from core.database import get_session
from crawl import get_subscription_registry, SubscriptionSyncContext, SubscriptionSyncResult
from urllib.parse import urlparse
from models.subscription import Subscription as SubscriptionModel
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_service, subscription_sync_state_service, video_service
from utils.metrics import metrics
from .base import UpdateStrategy
from ..models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger

logger = logging.getLogger()


class DefaultUpdateStrategy(UpdateStrategy):
    """默认更新策略（适用于所有站点）"""

    @property
    def site_name(self) -> str:
        return "default"
    
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, Optional[str]]:
        """检查是否需要更新"""
        sub = subscription_service.get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, "subscription_not_found"
        return True, None
    
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> SubscriptionSyncResult:
        """获取视频列表"""
        subscription_registry = get_subscription_registry()
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc.lower().split(':')[0]
        subscription_key = subscription_registry.get_by_domain(domain)
        if not subscription_key:
            raise ValueError(f"No subscription handler found for domain: {domain}")
        subscription_cls = subscription_registry.get(subscription_key)
        if not subscription_cls or not isinstance(subscription_cls, type):
            raise ValueError(f"Invalid subscription class for key: {subscription_key}")
        subscribe_channel = subscription_cls(url=request.url)

        sync_state = subscription_sync_state_service.get_sync_state_by_id(request.sync_state_id) if request.sync_state_id else None
        sync_mode = UpdateMode.FULL if request.mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        context = SubscriptionSyncContext(
            mode=sync_mode.value,
            cursor_payload=(sync_state.cursor_payload if sync_state else None) or {},
            last_seen_video_url=sync_state.last_seen_video_url if sync_state else None,
            limit=None if sync_mode == UpdateMode.FULL else settings.CHANNEL_UPDATE_DEFAULT_SIZE,
        )
        result = subscribe_channel.sync_videos(context)

        if sync_mode == UpdateMode.FULL and result.total_available is not None:
            self._update_total_videos(request.subscription_id, result.total_available)

        return result
    
    def enqueue_extraction(self, fetch_result: SubscriptionSyncResult, request: SubscriptionUpdateRequest) -> int:
        """将视频加入提取队列"""
        enqueued = 0
        existing_count = 0
        failed_count = 0
        vip_count = 0
        is_full_update = request.mode == UpdateMode.FULL
        video_urls = fetch_result.video_urls
        total = len(fetch_result.video_urls)
        existing_videos = video_service.get_videos_by_urls(video_urls)

        # 获取站点信息用于指标
        domain = subscription_sync_state_service._resolve_site(request.url) or "unknown"

        # 批量检查VIP视频
        from services.vip_video_service import is_vip_video
        vip_video_urls = set()
        with get_session() as session:
            for video_url in video_urls:
                if is_vip_video(video_url, session):
                    vip_video_urls.add(video_url)

        for video_url in video_urls:
            existing_video = existing_videos.get(video_url)
            if existing_video:
                existing_count += 1
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_in_db"})
            elif video_url in vip_video_urls:
                vip_count += 1
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "vip_video"})
            else:
                try:
                    params = VideoExtractDto(
                        url=video_url,
                        subscribed=True,
                        only_extract=True,
                        subscription_id=request.subscription_id,
                        sync_state_id=request.sync_state_id,
                        is_manual=request.trigger == UpdateTrigger.MANUAL,
                        is_extract_all=is_full_update
                    )
                    if download_service.enqueue_video_extraction(params):
                        enqueued += 1
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to enqueue video {video_url}: {e}")

        subscription_sync_state_service.increment_pending_video_count(request.sync_state_id, enqueued)

        logger.debug(
            "Enqueue summary subscription_id=%s domain=%s trigger=%s mode=%s total=%s queued=%s existed=%s vip=%s failed=%s",
            request.subscription_id,
            domain,
            request.trigger.value,
            request.mode.value,
            total,
            enqueued,
            existing_count,
            vip_count,
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

