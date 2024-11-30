from consumer.base import redis_broker
import dramatiq

dramatiq.set_broker(redis_broker)

from consumer.download_task import process_download_message
from consumer.extract_task import (
    process_extract_message,
    process_extract_bilibili_message,
    process_extract_youtube_message,
    process_extract_pornhub_message,
    process_extract_javdb_message
)
from consumer.subscribe_task import process_subscribe_message
from consumer.video_progress_task import process_video_progress_message

__all__ = [
    'redis_broker',
    'process_download_message',
    'process_extract_message',
    'process_extract_bilibili_message',
    'process_extract_youtube_message',
    'process_extract_pornhub_message',
    'process_extract_javdb_message',
    'process_subscribe_message',
    'process_video_progress_message'
]