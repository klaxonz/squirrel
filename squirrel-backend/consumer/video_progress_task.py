import json
import logging

import dramatiq
from common import constants
from services.video_history_service import VideoHistoryService

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_PROGRESS_TASK)
def process_video_progress_message(message):
    logger.info(f"处理视频进度消息：{message}")
    data = json.loads(message)
    video_history_service = VideoHistoryService()
    video_history_service.update_watch_history(
        data['video_id'],
        data['channel_id'],
        data['watch_duration'],
        data['last_position'],
        data['total_duration']
    )
