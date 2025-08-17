import logging
from datetime import datetime, timezone
from redis.exceptions import LockError

from core.cache import DistributedLock
from services.subscription_progress_service import set_progress
from core.config import settings
from core.database import get_session
from dto.subscription_dto import SubscriptionDto
from dto.video_dto import VideoExtractDto
from models.subscription import Subscription
from services import download_service
from subscribe.factory import SubscriptionFactory

logger = logging.getLogger()

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
        try:
            with DistributedLock(
                lock_key,
                timeout=180,
                blocking_timeout=180,
                auto_renew=True,
                renew_interval=60,
                renew_extend=120,
            ):
                set_progress(sub.id, {"status": "in_progress", "phase": "fetching_feed", "source": "manual" if is_manual else "scheduled"})

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

                set_progress(sub.id, {"phase": "extracting", "total": len(extract_list), "processed": 0})

                if len(extract_list) == 0:
                    set_progress(sub.id, {
                        "status": "completed",
                        "phase": "finalizing",
                        "finishedAt": datetime.now(timezone.utc).isoformat()
                    })
                    return

                for video in extract_list:
                    params = VideoExtractDto(
                        url=video,
                        subscribed=True,
                        only_extract=True,
                        subscription_id=sub.id,
                        is_manual=is_manual
                    )
                    download_service.start(params)
        except LockError:
            logger.info(f"Update already in progress for subscription {sub.id}")
            return
        except Exception as e:
            logger.error(f"Unexpected error while updating subscription {sub.id}: {e}", exc_info=True)
            return

