import json
import logging
from datetime import datetime

from common import constants
from common.cache import RedisClient
from common.config import GlobalConfig
from common.database import get_session
from common.message_queue import RedisMessageQueue
from common.url_helper import extract_top_level_domain
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from downloader.id_extractor import extract_id_from_url
from meta.video import VideoFactory
from model.channel import ChannelVideo
from model.download_task import DownloadTask, DownloadTaskSchema
from model.message import Message

logger = logging.getLogger(__name__)


class ChannelVideoExtractAndDownloadConsumerThread(BaseConsumerThread):
    def run(self):
        while self.running:
            try:
                message = self._dequeue_message()
                if message:
                    self._process_message(message)
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def _dequeue_message(self):
        with get_session() as session:
            message = self.mq.wait_and_dequeue(session=session, timeout=5)
            if message:
                self.handle_message(message, session=session)
                session.expunge(message)
        return message

    def _process_message(self, message):
        extract_info = json.loads(message.body)
        url = extract_info['url']
        domain = extract_top_level_domain(url)
        video_id = extract_id_from_url(url)

        channel_video = self._get_channel_video(domain, video_id)

        if self._should_skip_extraction(extract_info, channel_video):
            return

        video_info = self._get_video_info(url)
        if not video_info:
            return

        video = VideoFactory.create_video(url, video_info)
        uploader = video.get_uploader()
        if not uploader.name:
            logger.info(f"{url} uploader name is None, skip")
            return

        self._handle_video_extraction(extract_info, video, domain, video_id, video_info)

        if extract_info['if_only_extract']:
            return

        self._handle_download_task(extract_info, video, domain, video_id, channel_video)

    def _get_channel_video(self, domain, video_id):
        with get_session() as session:
            channel_video = session.query(ChannelVideo).filter(
                ChannelVideo.domain == domain,
                ChannelVideo.video_id == video_id
            ).first()
            if channel_video:
                session.expunge(channel_video)
        return channel_video

    def _should_skip_extraction(self, extract_info, channel_video):
        if extract_info['if_only_extract'] and channel_video is not None:
            self._update_redis_cache(channel_video.domain, channel_video.video_id, 'if_extract')
            logger.debug(f"视频已解析：{channel_video.url}")
            return True
        return False

    def _get_video_info(self, url):
        video_info = Downloader.get_video_info_thread(url, self.get_queue_thread_name())
        if video_info is None:
            logger.info(f"{url} is not a video, skip")
            return None
        if '_type' in video_info and video_info['_type'] == 'playlist':
            logger.info(f"{url} is a playlist, skip")
            return None
        return video_info

    def _handle_video_extraction(self, extract_info, video, domain, video_id, video_info):
        logger.debug(f"开始解析视频：channel {video.get_uploader().name}, video: {video.url}")
        if extract_info['if_subscribe'] and not self._get_channel_video(domain, video_id):
            self._create_channel_video(video, domain, video_id, video_info)
        logger.debug(f"结束解析视频：channel {video.get_uploader().name}, video: {video.url}")

    def _create_channel_video(self, video, domain, video_id, video_info):
        uploader = video.get_uploader()
        with get_session() as session:
            channel_video = ChannelVideo()
            channel_video.url = video.url,
            channel_video.domain = domain,
            channel_video.video_id = video_id,
            channel_video.channel_id = uploader.id,
            channel_video.channel_name = uploader.name,
            channel_video.channel_url = uploader.url,
            channel_video.channel_avatar = uploader.avatar,
            channel_video.title = video.get_title(),
            channel_video.thumbnail = video.get_thumbnail(),
            channel_video.duration = video.get_duration(),
            channel_video.uploaded_at = datetime.fromtimestamp(int(video_info['timestamp']))
            session.add(channel_video)
            session.commit()
        self._update_redis_cache(domain, video_id, 'if_extract')

    def _handle_download_task(self, extract_info, video, domain, video_id, channel_video):
        if extract_info['if_subscribe'] and channel_video and channel_video.if_downloaded:
            return

        logger.info(f"开始生成视频任务：channel {video.get_uploader().name}, video: {video.url}")

        download_task = self._get_or_create_download_task(video, domain, video_id)

        if self._should_skip_download(extract_info, download_task):
            return

        self._create_download_message(download_task)

        logger.info(f"结束生成视频任务：channel {video.get_uploader().name}, video: {video.url}")

    def _get_or_create_download_task(self, video, domain, video_id):
        with get_session() as session:
            download_task = session.query(DownloadTask).filter(
                DownloadTask.domain == domain,
                DownloadTask.video_id == video_id
            ).first()
            if download_task:
                session.expunge(download_task)
            else:
                download_task = self._create_download_task(video, domain, video_id)
        return download_task

    def _create_download_task(self, video, domain, video_id):
        uploader = video.get_uploader()
        with get_session() as session:
            download_task = DownloadTask()
            download_task.url = video.url,
            download_task.domain = domain,
            download_task.title = video.get_title(),
            download_task.thumbnail = video.get_thumbnail(),
            download_task.video_id = video_id,
            download_task.status = "PENDING",
            download_task.channel_id = uploader.id,
            download_task.channel_url = uploader.url,
            download_task.channel_name = uploader.name,
            download_task.channel_avatar = uploader.avatar
            session.add(download_task)
            session.commit()
            session.expunge(download_task)
        return download_task

    def _should_skip_download(self, extract_info, download_task):
        if download_task and not extract_info['if_retry'] and not extract_info['if_manual_retry']:
            self._update_redis_cache(download_task.domain, download_task.video_id, 'if_download')
            logger.info(f"视频已生成任务：channel {download_task.channel_name}, video: {download_task.url}")
            return True
        if download_task and download_task.status == 'COMPLETED':
            logger.info(f"视频已下载：channel {download_task.channel_name}, video: {download_task.url}")
            return True
        if download_task and not extract_info[
            'if_manual_retry'] and download_task.retry >= GlobalConfig.DOWNLOAD_RETRY_THRESHOLD:
            logger.info(f"视频下载已超过重试次数：channel {download_task.channel_name}, video: {download_task.url}")
            return True
        return False

    def _create_download_message(self, download_task):
        with get_session() as session:
            message = Message()
            message.body = DownloadTaskSchema().dumps(download_task)
            session.add(message)
            session.commit()
            RedisMessageQueue(queue_name=constants.QUEUE_DOWNLOAD_TASK).enqueue(message)
            message.send_status = 'SENDING'
            session.commit()

    def _update_redis_cache(self, domain, video_id, cache_key):
        client = RedisClient.get_instance().client
        key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}"
        client.hset(key, cache_key, datetime.now().timestamp())
