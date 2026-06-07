"""Video persistence service - handles video database operations
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_session
from models.video import Video as VideoModel
from services import subscription_video_service, user_video_feed_service
from utils import url_helper

logger = logging.getLogger(__name__)


class VideoPersistenceService:
    """Video persistence service

    Responsibilities:
    - Create or update video records
    - Create subscription-video associations
    - Update subscription statistics
    """

    def create_or_update(
        self,
        url: str,
        title: str,
        thumbnail: str | None = None,
        duration: int | None = None,
        publish_date: datetime | None = None,
        description: str | None = None,
        subscription_id: int | None = None,
        subscription_sync_mode: str | None = None,
    ) -> tuple[VideoModel, bool]:
        """Create or update a video record

        Args:
            url: Video URL
            title: Video title
            thumbnail: Thumbnail URL
            duration: Duration in seconds
            publish_date: Publish date
            description: Video description
            subscription_id: Subscription ID
            subscription_sync_mode: Subscription sync mode, full or incremental

        Returns:
            (video_model, is_new): Video model and whether it was newly created

        """
        with get_session() as session:
            # Query if already exists
            video = session.scalars(
                select(VideoModel).where(VideoModel.url == url),
            ).first()

            is_new = video is None

            if is_new:
                # Create new video
                if publish_date is None:
                    logger.warning("Missing publish_date when creating video: url=%s", url)

                video = VideoModel(
                    url=url,
                    domain=url_helper.normalize_domain(url),
                    title=title,
                    thumbnail=thumbnail,
                    duration=duration,
                    publish_date=publish_date,
                    description=description,
                )

                session.add(video)
                session.commit()
                session.refresh(video)

                logger.info("Created new video: id=%s, url=%s", video.id, url)
            else:
                updated = False

                normalized_domain = url_helper.normalize_domain(url)
                if normalized_domain and normalized_domain != video.domain:
                    video.domain = normalized_domain
                    updated = True

                if title and title != video.title:
                    video.title = title
                    updated = True

                if thumbnail is not None and thumbnail != video.thumbnail:
                    video.thumbnail = thumbnail
                    updated = True


                if duration is not None and duration != video.duration:
                    video.duration = duration
                    updated = True

                if publish_date is not None and publish_date != video.publish_date:
                    video.publish_date = publish_date
                    updated = True

                if description is not None and description != video.description:
                    video.description = description
                    updated = True

                if updated:
                    session.commit()
                    session.refresh(video)
                    user_video_feed_service.refresh_video_feed_metadata(video.id)
                    logger.info("Updated video: id=%s, url=%s", video.id, url)
                else:
                    logger.debug("Video already exists: id=%s, url=%s", video.id, url)

            # Create subscription-video link (if subscription_id provided)
            if subscription_id:
                self._create_subscription_link(
                    session,
                    subscription_id,
                    video.id,
                    is_new,
                    subscription_sync_mode=subscription_sync_mode,
                )

            return video, is_new

    def _create_subscription_link(
        self,
        session: Session,
        subscription_id: int,
        video_id: int,
        is_new_video: bool,
        *,
        subscription_sync_mode: str | None,
    ) -> None:
        """Create subscription-video association"""
        try:
            refresh_feed = subscription_sync_mode == "incremental"
            _, created_new_link = subscription_video_service.create_subscription_video(
                subscription_id,
                video_id,
                refresh_feed=refresh_feed,
            )

            if created_new_link:
                logger.debug("Created subscription-video link: subscription_id=%s, video_id=%s, is_new_video=%s, sync_mode=%s", subscription_id, video_id, is_new_video, subscription_sync_mode)

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to create subscription-video link: subscription_id=%s, video_id=%s, error=%s", subscription_id, video_id, e)
            # Do not raise, allow continuation


# Singleton instance
video_persistence_service = VideoPersistenceService()
