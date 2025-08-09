import logging
from datetime import datetime, timezone
from typing import Dict, Any

from core.cache import DistributedLock, RedisClient
from core.config import settings
from core.database import get_session
from dto.subscription_dto import SubscriptionDto
from dto.video_dto import VideoExtractDto
from models.subscription import Subscription
from services import download_service
from subscribe.factory import SubscriptionFactory
from common import constants

logger = logging.getLogger()
client = RedisClient.get_instance().get_client()


def _progress_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX}{sub_id}"


def _set_progress(sub_id: int, data: Dict[str, Any]) -> None:
    base = {"subscriptionId": sub_id, "updatedAt": datetime.now(timezone.utc).isoformat()}
    client.hset(_progress_key(sub_id), mapping={**base, **data})
    client.expire(_progress_key(sub_id), 24 * 3600)


class SubscriptionUpdateService:
    """Encapsulate subscription video update strategy and side effects."""

    @staticmethod
    def _should_extract_all(sub: SubscriptionDto) -> bool:
        if sub.total_videos == 0:
            return True
        if sub.total_videos - sub.total_extract <= settings.CHANNEL_UPDATE_DEFAULT_SIZE:
            return False
        return True

    @staticmethod
    def update_subscription_videos(sub: SubscriptionDto, is_manual: bool = False) -> None:
        lock_key = f"lock:subscription:update:{sub.id}"
        lock = DistributedLock(lock_key)
        acquired = lock.acquire(timeout=30)
        if not acquired:
            logger.info(f"Update already in progress for subscription {sub.id}")
            return
        try:
            # 进度：准备抓取订阅列表
            _set_progress(sub.id, {"status": "in_progress", "phase": "fetching_feed", "source": "manual" if is_manual else "scheduled"})

            subscribe_channel = SubscriptionFactory.create_subscription(sub.url)
            is_extract_all = SubscriptionUpdateService._should_extract_all(sub)
            video_list = subscribe_channel.get_subscribe_videos(extract_all=is_extract_all)
            if is_extract_all:
                with get_session() as session:
                    session.query(Subscription).filter(Subscription.id == sub.id).update({
                        Subscription.total_videos: len(video_list)
                    })
                    session.commit()

            extract_list = video_list if is_extract_all else video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]

            # 进度：进入解析阶段，设置总数与 processed=0
            _set_progress(sub.id, {"phase": "extracting", "total": len(extract_list), "processed": 0})

            for video in extract_list:
                params = VideoExtractDto(
                    url=video,
                    subscribed=True,
                    only_extract=True,
                    subscription_id=sub.id,
                    is_manual=is_manual
                )
                download_service.start(params)
        finally:
            lock.release()

