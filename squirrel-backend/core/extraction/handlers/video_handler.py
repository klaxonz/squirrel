"""
视频提取结果处理器
"""
import logging
from datetime import datetime

from core.database import get_session
from core.progress import progress_emitter, ProgressEvent, ProgressEventType
from crawl import ExtractionTask, ExtractionResult, Video
from models.subscription import Subscription
from services import (
    video_service, subscription_video_service, creator_service,
    video_creator_service, task_service, message_service
)
from mq.producer import RedisStreamProducer
from common import constants
from ..base import BaseResultHandler

logger = logging.getLogger()


class VideoExtractionHandler(BaseResultHandler):
    """视频提取结果处理器"""

    def __init__(self):
        self.redis_producer = RedisStreamProducer()

    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理成功结果"""
        try:
            subscription_id = task.metadata.get('subscription_id')
            
            if result.success is False:
                logger.info(f"提取任务结果失败: {task.task_id}")
                # 发射失败事件
                if subscription_id:
                    progress_emitter.emit(ProgressEvent(
                        event_type=ProgressEventType.VIDEO_EXTRACTION_ERROR,
                        subscription_id=subscription_id,
                        url=task.url,
                        error="提取结果失败"
                    ))
                return

            # 获取任务元数据
            only_extract = task.metadata.get('only_extract', True)
            subscribed = task.metadata.get('subscribed', False)
            is_extract_all = task.metadata.get('is_extract_all', False)

            if not subscription_id:
                logger.info(f"任务缺少subscription_id: {task.task_id}")
                return

            # 检查订阅是否存在
            if not self._check_subscription_exist(subscription_id):
                logger.info(f"订阅不存在或已删除: {subscription_id}")
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_ERROR,
                    subscription_id=subscription_id,
                    url=task.url,
                    error="订阅不存在或已删除"
                ))
                return

            # 创建或更新视频记录
            video = None
            video_status = "unknown"
            if subscribed:
                video, video_status = self._create_or_update_video(
                    task, result, subscription_id, is_extract_all
                )

            # 发射成功事件
            if video:
                video_title = result.data.title if hasattr(result.data, 'title') else task.url
                message = f"提取成功: {video_title}"
                if video_status == "existed":
                    message = f"视频已存在: {video_title}"
                elif video_status == "created":
                    message = f"新视频: {video_title}"
                
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_COMPLETE,
                    subscription_id=subscription_id,
                    video_id=video.id,
                    url=task.url,
                    message=message,
                    metadata={'status': video_status}
                ))
            else:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_ERROR,
                    subscription_id=subscription_id,
                    url=task.url,
                    error="创建视频失败"
                ))

            # 如果需要下载，创建下载任务
            if not only_extract and video:
                self._create_download_task(video)


        except Exception as e:
            logger.error(f"处理成功结果失败: {task.task_id}, error: {e}", exc_info=True)
            # 发射异常事件
            subscription_id = task.metadata.get('subscription_id')
            if subscription_id:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_ERROR,
                    subscription_id=subscription_id,
                    url=task.url,
                    error=str(e)
                ))

    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理失败结果"""
        try:
            logger.error(f"处理视频提取失败结果: {task.task_id}, error: {result.error}")
            
            # 发射失败事件
            subscription_id = task.metadata.get('subscription_id')
            if subscription_id:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_ERROR,
                    subscription_id=subscription_id,
                    url=task.url,
                    error=result.error or "视频提取失败"
                ))

        except Exception as e:
            logger.error(f"处理失败结果异常: {task.task_id}, error: {e}")

    def _create_or_update_video(self, task: ExtractionTask, result: ExtractionResult, subscription_id: int, is_extract_all: bool):
        """
        创建或更新视频记录
        
        Returns:
            (video, status): 视频对象和状态 ('created', 'existed', 'error')
        """
        try:
            data = result.data

            if not isinstance(data, Video):
                logger.error(f"提取结果返回的 data 类型不是 Video: {type(data)}")
                return None, "error"

            with get_session():
                # 检查视频是否已存在
                video = video_service.get_video_by_url(task.url)
                video_status = "existed" if video else "created"

                if not video:
                    # 创建新视频
                    publish_date = self._resolve_publish_date(data)
                    video = video_service.create_video(
                        task.url,
                        data.title or task.url,
                        publish_date,
                        data.thumbnail,
                        data.duration
                    )

                # 创建订阅-视频关联
                _, created_new_link = subscription_video_service.create_subscription_video(
                    subscription_id, video.id
                )

                # 在增量更新时且确实新增了关联时，更新总数
                if not is_extract_all and created_new_link:
                    self._increment_subscription_total_videos(subscription_id)

                # 处理演员信息
                self._process_actors(video, data)

                return video, video_status

        except Exception as e:
            logger.error(f"创建或更新视频失败: {task.url}, error: {e}")
            return None, "error"

    def _process_actors(self, video, video_meta: Video):
        """处理演员信息"""
        try:
            actors = video_meta.actors
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

    def _resolve_publish_date(self, video_meta: Video):
        """根据 Video 对象推断发布时间"""
        try:
            # 直接使用 Video 对象的 publish_date，如果没有则使用当前时间
            publish_date = getattr(video_meta, 'publish_date', None)
            if publish_date:
                return publish_date
                
            upload_date = getattr(video_meta, 'upload_date', None)
            if upload_date:
                for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d'):
                    try:
                        return datetime.strptime(str(upload_date), fmt)
                    except ValueError:
                        continue

        except Exception as e:
            logger.debug(f"解析发布时间失败，使用当前时间: {e}")
            raise  # 抛出异常


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
