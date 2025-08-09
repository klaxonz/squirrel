import json
import logging
from typing import Dict, Any

from common import constants
from core.database import get_session
from downloader.factory import DownloaderFactory
from models.task.download_task import DownloadTask
from models.message import Message
from models.task.task_state import TaskState
from services import video_service, subscription_video_service, task_service
from services import subscription_service
from consumer.queue_management.decorators import queue_handler
from consumer.queue_management.manager import QueueManager

logger = logging.getLogger(__name__)


@queue_handler(constants.QUEUE_VIDEO_DOWNLOAD)
def process_download_message(message: Dict[str, Any]):
    _process_download_message_unified(message)


@queue_handler(constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED)
def process_download_scheduled_message(message: Dict[str, Any]):
    _process_download_message_unified(message)


def _process_download_message_unified(message: Dict[str, Any]):
    try:
        logger.info(f"开始处理下载任务: {message}")

        message_obj = Message.from_dict(message)
        video, download_task, subscription = _prepare_download_task(message_obj)

        downloader = DownloaderFactory.create_downloader(video.url)
        task_state = downloader.download(subscription, video, download_task, "video_download")

        task_service.update_task_status(download_task.id, task_state)

        logger.info(f"视频下载完成: {video.title}, URL: {video.url}")

    except Exception as e:
        logger.error(f"处理下载任务时发生错误: {e}", exc_info=True)
        raise


@queue_handler("video_download_priority_*")
def process_priority_download(message: Dict[str, Any], queue_name: str):
    try:
        priority = queue_name.split('_')[-1] if '_' in queue_name else 'normal'

        logger.info(f"开始处理优先级下载任务: priority={priority}")

        # 根据优先级设置不同的处理参数
        if priority == 'high':
            timeout = 300  # 5分钟
            max_concurrent = 3
        elif priority == 'urgent':
            timeout = 180  # 3分钟
            max_concurrent = 1  # 独占处理
        else:
            timeout = 600  # 10分钟
            max_concurrent = 2

        # 添加优先级信息到消息
        message['_priority'] = priority
        message['_timeout'] = timeout
        message['_max_concurrent'] = max_concurrent

        # 调用标准下载处理器
        process_download_message(message)

    except Exception as e:
        logger.error(f"优先级下载任务失败: priority={priority}, error={e}", exc_info=True)
        raise


@queue_handler("video_download_batch")
def process_batch_download(message: Dict[str, Any]):
    try:
        task_ids = message['task_ids']
        batch_id = message.get('batch_id', 'unknown')

        logger.info(f"开始批量下载: batch_id={batch_id}, 任务数={len(task_ids)}")

        results = []
        for task_id in task_ids:
            try:
                download_message = {
                    "body": json.dumps({"id": task_id})
                }

                QueueManager.send_message(constants.QUEUE_VIDEO_DOWNLOAD, download_message)
                results.append({"task_id": task_id, "status": "queued"})

            except Exception as e:
                logger.error(f"批量下载中单个任务失败: task_id={task_id}, error={e}")
                results.append({"task_id": task_id, "status": "failed", "error": str(e)})

        success_count = len([r for r in results if r['status'] == 'queued'])
        logger.info(f"批量下载完成: batch_id={batch_id}, 成功={success_count}/{len(task_ids)}")

    except Exception as e:
        logger.error(f"批量下载失败: {e}", exc_info=True)
        raise


def _prepare_download_task(message):
    with get_session() as session:
        download_task = DownloadTask.from_dict(json.loads(message.body))
        download_task = task_service.get_task_by_id(download_task.id)
        download_task = session.merge(download_task)
        video = video_service.get_video_by_id(download_task.video_id)
        subscription_video = subscription_video_service.get_subscription_video_by_video_id(video.id)
        subscription = subscription_service.get_subscription_by_id(subscription_video.subscription_id)
        download_task.transition_to(TaskState.DOWNLOADING.value)
        session.commit()
        return video, download_task, subscription


