"""
视频持久化服务 - 负责视频数据的数据库操作
"""
import logging
from typing import Tuple, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from core.database import get_session
from models.video import Video as VideoModel
from services import subscription_video_service
from services import user_video_feed_service
from utils import url_helper


logger = logging.getLogger(__name__)


class VideoPersistenceService:
    """
    视频持久化服务
    
    职责：
    - 创建或更新视频记录
    - 创建订阅-视频关联
    - 更新订阅统计
    """
    
    def create_or_update(
        self,
        url: str,
        title: str,
        thumbnail: Optional[str] = None,
        duration: Optional[int] = None,
        publish_date: Optional[datetime] = None,
        description: Optional[str] = None,
        subscription_id: Optional[int] = None,
        subscription_sync_mode: Optional[str] = None,
    ) -> Tuple[VideoModel, bool]:
        """
        创建或更新视频记录
        
        Args:
            url: 视频URL
            title: 标题
            thumbnail: 缩略图URL
            duration: 时长（秒）
            publish_date: 发布时间
            description: 描述
            subscription_id: 订阅ID
            subscription_sync_mode: 订阅同步模式，full 或 incremental
            
        Returns:
            (video_model, is_new): 视频模型和是否新创建
        """
        with get_session() as session:
            # 查询是否已存在
            video = session.scalars(
                select(VideoModel).where(VideoModel.url == url)
            ).first()

            is_new = video is None

            if is_new:
                # 创建新视频
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

                logger.info(f"Created new video: id={video.id}, url={url}")     
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
                    logger.info(f"Updated video: id={video.id}, url={url}")
                else:
                    logger.debug(f"Video already exists: id={video.id}, url={url}") 

            # 创建订阅-视频关联（如果提供了subscription_id）
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
        subscription_sync_mode: Optional[str],
    ) -> None:
        """创建订阅-视频关联"""
        try:
            refresh_feed = subscription_sync_mode == 'incremental'
            _, created_new_link = subscription_video_service.create_subscription_video(
                subscription_id,
                video_id,
                refresh_feed=refresh_feed,
            )

            if created_new_link:
                logger.debug(
                    f"Created subscription-video link: "
                    f"subscription_id={subscription_id}, video_id={video_id}, "
                    f"is_new_video={is_new_video}, sync_mode={subscription_sync_mode}"
                )
        
        except Exception as e:
            logger.error(
                f"Failed to create subscription-video link: "
                f"subscription_id={subscription_id}, video_id={video_id}, error={e}"
            )
            # 不抛出异常，允许继续


# 单例实例
video_persistence_service = VideoPersistenceService()
