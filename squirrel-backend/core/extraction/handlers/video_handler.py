"""
视频提取结果处理器
"""
import logging
from datetime import datetime
from typing import Dict, Any

from core.database import get_session
from models.subscription import Subscription
from services import (
    video_service, subscription_video_service, creator_service, 
    video_creator_service, task_service, message_service
)
from mq.producer import RedisStreamProducer
from common import constants
from models.message import Message

from ..interfaces import ExtractionTask, ExtractionResult, IResultHandler
from ..base import BaseResultHandler

logger = logging.getLogger(__name__)


class VideoExtractionHandler(BaseResultHandler):
    """视频提取结果处理器"""
    
    def __init__(self):
        self.redis_producer = RedisStreamProducer()
    
    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理成功结果"""
        try:
            logger.info(f"处理视频提取成功结果: {task.task_id}")
            
            # 获取提取结果数据
            video_info = result.data.get('video_info')
            video_meta = result.data.get('video_meta')
            
            if not video_info or not video_meta:
                logger.error(f"提取结果数据不完整: {task.task_id}")
                return
            
            # 获取任务元数据
            subscription_id = task.metadata.get('subscription_id')
            only_extract = task.metadata.get('only_extract', True)
            subscribed = task.metadata.get('subscribed', False)
            is_extract_all = task.metadata.get('is_extract_all', False)
            
            if not subscription_id:
                logger.warning(f"任务缺少subscription_id: {task.task_id}")
                return
            
            # 检查订阅是否存在
            if not self._check_subscription_exist(subscription_id):
                logger.warning(f"订阅不存在或已删除: {subscription_id}")
                return
            
            # 创建或更新视频记录
            video = None
            if subscribed:
                video = self._create_or_update_video(
                    task, video_info, video_meta, subscription_id, is_extract_all
                )
            
            # 如果需要下载，创建下载任务
            if not only_extract and video:
                self._create_download_task(video)
            
            
            logger.info(f"视频提取结果处理完成: {task.task_id}")
            
        except Exception as e:
            logger.error(f"处理成功结果失败: {task.task_id}, error: {e}", exc_info=True)
    
    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理失败结果"""
        try:
            logger.error(f"处理视频提取失败结果: {task.task_id}, error: {result.error}")
                
        except Exception as e:
            logger.error(f"处理失败结果异常: {task.task_id}, error: {e}")
    
    def _create_or_update_video(self, task: ExtractionTask, video_info: Dict[str, Any], 
                              video_meta: Any, subscription_id: int, is_extract_all: bool):
        """创建或更新视频记录"""
        try:
            with get_session():
                # 检查视频是否已存在
                video = video_service.get_video_by_url(task.url)
                
                if not video:
                    # 创建新视频
                    publish_date = datetime.fromtimestamp(video_info['timestamp'])
                    video = video_service.create_video(
                        task.url,
                        video_info['title'],
                        publish_date,
                        video_info['thumbnail'],
                        video_info['duration']
                    )
                
                # 创建订阅-视频关联
                _, created_new_link = subscription_video_service.create_subscription_video(
                    subscription_id, video.id
                )
                
                # 在增量更新时且确实新增了关联时，更新总数
                if not is_extract_all and created_new_link:
                    self._increment_subscription_total_videos(subscription_id)
                
                # 处理演员信息
                self._process_actors(video, video_meta)
                
                return video
                
        except Exception as e:
            logger.error(f"创建或更新视频失败: {task.url}, error: {e}")
            return None
    
    def _process_actors(self, video, video_meta):
        """处理演员信息"""
        try:
            actors = getattr(video_meta, 'actors', [])
            if not actors:
                return
            
            for actor_meta in actors:
                # 获取或创建演员
                creator = creator_service.get_creator_by_url(actor_meta.url)
                if not creator:
                    creator = creator_service.create_creator(
                        actor_meta.url, actor_meta.name, actor_meta.avatar
                    )
                
                # 创建视频-演员关联
                video_creator = video_creator_service.get_video_creator(video.id, creator.id)
                if not video_creator:
                    video_creator_service.create_video_creator(video.id, creator.id)
                    
        except Exception as e:
            logger.warning(f"处理演员信息失败: video_id={video.id}, error: {e}")
    
    def _increment_subscription_total_videos(self, subscription_id: int):
        """增加订阅的总视频数"""
        try:
            with get_session() as session:
                session.query(Subscription).filter(
                    Subscription.id == subscription_id
                ).update({
                    Subscription.total_videos: Subscription.total_videos + 1
                })
                session.commit()
        except Exception as e:
            logger.warning(f"更新订阅总视频数失败: {subscription_id}, error: {e}")
    
    def _create_download_task(self, video):
        """创建下载任务"""
        try:
            task = task_service.create_task(video.id, video.url)
            message = message_service.create_message(task.to_dict())
            
            self.redis_producer.send(constants.QUEUE_VIDEO_DOWNLOAD, message.to_dict())
            
            logger.info(f"下载任务已发送: video_id={video.id}")
            
        except Exception as e:
            logger.error(f"创建下载任务失败: video_id={video.id}, error: {e}")
    
    
    def _check_subscription_exist(self, subscription_id: int) -> bool:
        """检查订阅是否存在"""
        try:
            from services import subscription_service
            subscription = subscription_service.get_subscription_by_id(subscription_id)
            return subscription is not None and not subscription.is_deleted
        except Exception as e:
            logger.error(f"检查订阅存在性失败: subscription_id={subscription_id}, error: {e}")
            return False
