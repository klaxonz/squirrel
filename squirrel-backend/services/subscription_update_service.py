import logging
from redis.exceptions import LockError
from core.cache import DistributedLock
from core.config import settings
from core.database import get_session
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from schemas.video.dto.video_dto import VideoExtractDto
from models.subscription import Subscription
from services import download_service
from sites.subscription import SubscriptionFactory

logger = logging.getLogger()


class SubscriptionUpdateService:
    """Encapsulate subscription video update strategy and side effects."""

    @staticmethod
    def _should_extract_all(sub: SubscriptionDto) -> bool:
        # Full fetch when:
        # - Unknown total yet
        # - Already fully extracted (to detect new videos and refresh total)
        # - Backlog is small enough to process in one go (<= default window)
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
        try:
            with DistributedLock(
                    lock_key,
                    timeout=180,
                    blocking_timeout=180,
                    auto_renew=True,
                    renew_interval=60,
                    renew_extend=120,
            ):
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

                if len(extract_list) == 0:
                    return

                for video in extract_list:
                    params = VideoExtractDto(
                        url=video,
                        subscribed=True,
                        only_extract=True,
                        subscription_id=sub.id,
                        is_manual=is_manual,
                        is_extract_all=is_extract_all
                    )
                    download_service.start(params)
        except LockError:
            logger.info(f"Update already in progress for subscription {sub.id}")
            return
        except Exception as e:
            logger.error(f"Unexpected error while updating subscription {sub.id}: {e}", exc_info=True)
            return
