import logging
from typing import List
from sqlalchemy import select, update
from core.cache import get_distributed_lock
from core.config import settings
from core.database import get_session
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from schemas.video.dto.video_dto import VideoExtractDto
from models.subscription import Subscription
from services import download_service
from crawl import SubscriptionFactory

logger = logging.getLogger()


class SubscriptionUpdateService:
    """订阅视频更新服务"""

    @staticmethod
    def _should_extract_all(sub: SubscriptionDto) -> bool:
        if sub.total_videos <= 0:
            return True
        if sub.total_extract >= sub.total_videos:
            return True
        if (sub.total_videos - sub.total_extract) >= settings.CHANNEL_UPDATE_DEFAULT_SIZE:
            return True
        return False

    @staticmethod
    def update_subscription_videos(sub: SubscriptionDto, is_manual: bool = False) -> None:
        lock_key = f"lock:subscription:update:{sub.id}"
        lock = get_distributed_lock(lock_key, timeout=180, auto_renewal=True)
        
        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.info(f"Update already in progress for subscription {sub.id}")
            return
        
        try:
            subscribe_channel = SubscriptionFactory.create_subscription(sub.url)
            is_extract_all = SubscriptionUpdateService._should_extract_all(sub)
            video_list = subscribe_channel.get_subscribe_videos(extract_all=is_extract_all)
            
            if is_extract_all and video_list:
                SubscriptionUpdateService._update_total_videos(sub.id, len(video_list))

            extract_list = video_list if is_extract_all else video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]

            if not extract_list:
                logger.info(f"No videos to extract for subscription {sub.id}")
                return

            SubscriptionUpdateService._batch_enqueue_video_extraction(
                extract_list, 
                sub.id, 
                is_manual, 
                is_extract_all
            )
            
        except Exception as e:
            logger.error(f"Unexpected error while updating subscription {sub.id}: {e}", exc_info=True)
        finally:
            try:
                lock.release()
            except Exception as e:
                logger.warning(f"Failed to release lock for subscription {sub.id}: {e}")

    @staticmethod
    def _update_total_videos(subscription_id: int, total: int) -> None:
        with get_session() as session:
            session.execute(
                update(Subscription)
                .where(Subscription.id == subscription_id)
                .values(total_videos=total)
            )

    @staticmethod
    def _batch_enqueue_video_extraction(
        video_urls: List[str], 
        subscription_id: int, 
        is_manual: bool, 
        is_extract_all: bool
    ) -> None:
        for video_url in video_urls:
            params = VideoExtractDto(
                url=video_url,
                subscribed=True,
                only_extract=True,
                subscription_id=subscription_id,
                is_manual=is_manual,
                is_extract_all=is_extract_all
            )
            download_service.enqueue_video_extraction(params)
