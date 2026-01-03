"""
下载任务创建服务 - 负责创建视频下载任务
"""
import logging

from common import constants
from services import task_service, message_service
from queue.producer import RedisStreamProducer

logger = logging.getLogger(__name__)


class DownloadTaskCreatorService:
    """
    下载任务创建服务
    
    职责：
    - 创建下载任务
    - 发送到消息队列
    """
    
    def __init__(self):
        self.redis_producer = RedisStreamProducer()
    
    def create_download_task(self, video_model):
        """
        创建下载任务
        
        Args:
            video_model: 视频数据库模型
        """
        try:
            # 1. 创建任务记录
            task = task_service.create_task(video_model.id, video_model.url)
            
            # 2. 创建消息
            message = message_service.create_message(task.to_dict())
            
            # 3. 发送到队列
            self.redis_producer.send(
                constants.QUEUE_VIDEO_DOWNLOAD,
                message.to_dict()
            )
            
            logger.info(
                f"Download task created and enqueued: "
                f"video_id={video_model.id}, task_id={task.id}"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to create download task: "
                f"video_id={video_model.id}, error={e}",
                exc_info=True
            )
            # 不抛出异常，允许继续


# 单例实例
download_task_creator_service = DownloadTaskCreatorService()
