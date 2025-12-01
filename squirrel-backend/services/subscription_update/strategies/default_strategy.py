"""
默认更新策略（适用于所有站点）
"""
import logging
from typing import List, Optional
from sqlalchemy import update
from core.cache import get_distributed_lock
from core.config import settings
from core.database import get_session
from crawl import SubscriptionFactory
from models.subscription import Subscription
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_service, video_service
from .base import UpdateStrategy
from ..models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger

logger = logging.getLogger()


class DefaultUpdateStrategy(UpdateStrategy):
    """默认更新策略（适用于所有站点）"""
    
    def __init__(self):
        self._lock = None
    
    @property
    def site_name(self) -> str:
        return "default"
    
    def should_update(self, request: SubscriptionUpdateRequest) -> tuple[bool, Optional[str]]:
        """检查是否需要更新"""
        sub = subscription_service.get_subscription_detail(request.subscription_id)
        if not sub or sub.is_deleted:
            return False, "subscription_not_found"
        
        if not request.force:
            lock_key = f"lock:subscription:update:{request.subscription_id}"
            self._lock = get_distributed_lock(lock_key, timeout=180, auto_renewal=True)
            if not self._lock.acquire(blocking=False):
                return False, "update_in_progress"
        
        return True, None
    
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> List[str]:
        """获取视频列表"""
        subscribe_channel = SubscriptionFactory.create_subscription(request.url)
        
        # 直接根据 request.mode 判断是否全量提取
        is_full_update = request.mode == UpdateMode.FULL
        
        video_list = subscribe_channel.get_subscribe_videos(extract_all=is_full_update)
        
        # 全量更新时，更新总视频数
        if is_full_update and video_list:
            self._update_total_videos(request.subscription_id, len(video_list))
        
        # 全量更新返回所有视频，增量更新只返回最新的 N 个
        if is_full_update:
            return video_list
        else:
            return video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
    
    def enqueue_extraction(self, video_urls: List[str], request: SubscriptionUpdateRequest) -> int:
        """将视频加入提取队列"""
        enqueued = 0
        existing_count = 0
        failed_count = 0
        is_manual = request.trigger == UpdateTrigger.MANUAL
        is_full_update = request.mode == UpdateMode.FULL
        total = len(video_urls)
        existing_videos = video_service.get_videos_by_urls(video_urls)
        
        for index, video_url in enumerate(video_urls, 1):
            existing_video = existing_videos.get(video_url)
            if existing_video:
                existing_count += 1
            else:
                try:
                    params = VideoExtractDto(
                        url=video_url,
                        subscribed=True,
                        only_extract=True,
                        subscription_id=request.subscription_id,
                        is_manual=is_manual,
                        is_extract_all=is_full_update
                    )
                    download_service.enqueue_video_extraction(params)
                    enqueued += 1
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to enqueue video {video_url}: {e}")

        logger.debug(
            "Enqueue summary subscription_id=%s domain=%s trigger=%s mode=%s total=%s queued=%s existed=%s failed=%s",
            request.subscription_id,
            getattr(request, 'domain', None) or "-",
            request.trigger.value,
            request.mode.value,
            total,
            enqueued,
            existing_count,
            failed_count,
        )
        return enqueued
    
    def execute(self, request: SubscriptionUpdateRequest) -> 'SubscriptionUpdateResult':
        """执行更新流程（覆盖以支持锁释放）"""
        try:
            return super().execute(request)
        finally:
            if self._lock:
                try:
                    self._lock.release()
                except Exception as e:
                    logger.warning(f"Failed to release lock for subscription {request.subscription_id}: {e}")
    
    @staticmethod
    def _update_total_videos(subscription_id: int, total: int) -> None:
        """更新订阅总视频数"""
        with get_session() as session:
            session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(total_videos=total)
            )

