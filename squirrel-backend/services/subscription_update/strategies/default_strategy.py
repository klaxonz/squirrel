"""
默认更新策略（适用于所有站点）
"""
import logging
from typing import List, Optional
from sqlalchemy import update
from core.cache import get_distributed_lock
from core.config import settings
from core.database import get_session
from crawl import get_subscription_registry, Subscription
from urllib.parse import urlparse
from models.subscription import Subscription
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_service, video_service
from utils.metrics import metrics
from utils import url_helper
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
        
        # 检查队列积压情况（仅针对定时触发的增量更新）
        if request.trigger == UpdateTrigger.SCHEDULED and request.mode == UpdateMode.INCREMENTAL:
            from queues.queue_monitor import queue_monitor
            from core.config import settings
            
            should_skip, pending_count = queue_monitor.should_skip_subscription_update(
                subscription_id=request.subscription_id,
                url=request.url,
                threshold_ratio=0.5,  # 超过一半
                incremental_size=settings.CHANNEL_UPDATE_DEFAULT_SIZE
            )
            
            if should_skip:
                logger.info(
                    f"Skip subscription {request.subscription_id} update due to backpressure: "
                    f"pending_videos={pending_count}"
                )
                return False, "queue_backpressure"
        
        return True, None
    
    def fetch_videos(self, request: SubscriptionUpdateRequest) -> List[str]:
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
        subscribe_channel: Subscription = subscription_cls(url=request.url)

        is_full_update = request.mode == UpdateMode.FULL
        need_fetch_all = is_full_update

        if not is_full_update:
            sub = subscription_service.get_subscription_detail(request.subscription_id)
            if sub and sub.total_videos > 0 and sub.total_extract >= sub.total_videos:
                logger.info(
                    f"Subscription {request.subscription_id} extracted videos ({sub.total_extract}) "
                    f">= total_videos ({sub.total_videos}), fetching all videos to update total_videos"
                )
                need_fetch_all = True

        video_list = subscribe_channel.get_subscribe_videos(extract_all=need_fetch_all)

        if video_list and (is_full_update or need_fetch_all):
            sub = subscription_service.get_subscription_detail(request.subscription_id)
            if sub and len(video_list) > sub.total_extract:
                self._update_total_videos(request.subscription_id, len(video_list))

        if is_full_update:
            return video_list
        else:
            return video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
    
    def enqueue_extraction(self, video_urls: List[str], request: SubscriptionUpdateRequest) -> int:
        """将视频加入提取队列"""
        enqueued = 0
        existing_count = 0
        failed_count = 0
        vip_count = 0
        is_manual = request.trigger == UpdateTrigger.MANUAL
        is_full_update = request.mode == UpdateMode.FULL
        total = len(video_urls)
        existing_videos = video_service.get_videos_by_urls(video_urls)

        # 获取站点信息用于指标
        try:
            domain = url_helper.extract_top_level_domain(request.url)
        except Exception:
            domain = "unknown"

        # 批量检查VIP视频
        from services.vip_video_service import vip_video_service
        from core.database import get_session
        vip_video_urls = set()
        with get_session() as session:
            for video_url in video_urls:
                if vip_video_service.is_vip_video(video_url, session):
                    vip_video_urls.add(video_url)

        for index, video_url in enumerate(video_urls, 1):
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
                        is_manual=is_manual,
                        is_extract_all=is_full_update
                    )
                    download_service.enqueue_video_extraction(params)
                    enqueued += 1
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to enqueue video {video_url}: {e}")

        logger.debug(
            "Enqueue summary subscription_id=%s domain=%s trigger=%s mode=%s total=%s queued=%s existed=%s vip=%s failed=%s",
            request.subscription_id,
            getattr(request, 'domain', None) or "-",
            request.trigger.value,
            request.mode.value,
            total,
            enqueued,
            existing_count,
            vip_count,
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

