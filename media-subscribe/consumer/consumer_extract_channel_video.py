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
            url = None
            try:
                with get_session() as session:
                    message = self.mq.wait_and_dequeue(session=session, timeout=5)
                    if message:
                        self.handle_message(message, session=session)
                        session.expunge(message)
                url = None
                if message:
                    extract_info = json.loads(message.body)

                    url = extract_info['url']
                    domain = extract_top_level_domain(url)
                    video_id = extract_id_from_url(url)

                    if_retry = extract_info['if_retry']
                    if_subscribe = extract_info['if_subscribe']
                    if_only_extract = extract_info['if_only_extract']
                    if_manual_retry = extract_info['if_manual_retry']

                    with get_session() as session:
                        channel_video = session.query(ChannelVideo).where(ChannelVideo.domain == domain,
                                                                          ChannelVideo.video_id == video_id).first()
                        if channel_video:
                            session.expunge(channel_video)

                    if if_only_extract and channel_video is not None:
                        client = RedisClient.get_instance().client
                        key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}"
                        client.hset(key, 'if_extract', 1)
                        logger.debug(f"视频已解析：{url}")
                        continue

                    # 视频基本信息
                    video_info = Downloader.get_video_info_thread(url, self.get_queue_thread_name())
                    if video_info is None:
                        logger.info(f"{url} is not a video, skip")
                        continue
                    if '_type' in video_info and video_info['_type'] == 'playlist':
                        logger.info(f"{url} is a playlist, skip")
                        continue

                    video = VideoFactory.create_video(url, video_info)
                    uploader = video.get_uploader()
                    if uploader.name is None:
                        logger.info(f"{url} uploader name is None, skip")
                        continue

                    logger.debug(f"开始解析视频：channel {video.get_uploader().name}, video: {url}")
                    if if_subscribe and channel_video is None:
                        uploader = video.get_uploader()

                        with get_session() as session:
                            channel_video = ChannelVideo()
                            channel_video.url = url
                            channel_video.domain = domain
                            channel_video.video_id = video_id
                            channel_video.channel_id = uploader.id
                            channel_video.channel_name = uploader.name
                            channel_video.channel_url = uploader.url
                            channel_video.channel_avatar = uploader.avatar
                            channel_video.title = video.get_title()
                            channel_video.thumbnail = video.get_thumbnail()
                            channel_video.uploaded_at = datetime.fromtimestamp(int(video_info['timestamp']))
                            session.add(channel_video)
                            session.commit()
                            session.expunge(channel_video)

                        client = RedisClient.get_instance().client
                        key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}"
                        client.hset(key, 'if_extract', 1)

                    logger.debug(f"结束解析视频：channel {video.get_uploader().name}, video: {url}")
                    if if_only_extract:
                        continue

                    if if_subscribe and channel_video:
                        if channel_video.if_downloaded:
                            continue

                    # 下载任务
                    logger.info(f"开始生成视频任务：channel {video.get_uploader().name}, video: {url}")

                    with get_session() as session:
                        download_task = session.query(DownloadTask).where(DownloadTask.domain == domain,
                                                                          DownloadTask.video_id == video_id).first()
                        if download_task:
                            session.expunge(download_task)

                    if download_task and not if_retry and not if_manual_retry:
                        key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{download_task.domain}:{download_task.video_id}"
                        client = RedisClient.get_instance().client
                        client.hset(key, 'if_download', 1)
                        logger.info(f"视频已生成任务：channel {video.get_uploader().name}, video: {url}")
                        continue
                    if download_task and download_task.status == 'COMPLETED':
                        logger.info(f"视频已下载：channel {video.get_uploader().name}, video: {url}")
                        continue
                    if download_task and not if_manual_retry and download_task.retry >= GlobalConfig.DOWNLOAD_RETRY_THRESHOLD:
                        logger.info(f"视频下载已超过重试次数：channel {video.get_uploader().name}, video: {url}")
                        continue

                    if download_task is None:
                        uploader = video.get_uploader()

                        with get_session() as session:
                            download_task = DownloadTask()
                            download_task.url = url
                            download_task.domain = domain
                            download_task.title = video.get_title()
                            download_task.thumbnail = video.get_thumbnail()
                            download_task.video_id = video_id
                            download_task.status = "PENDING"
                            download_task.channel_id = uploader.id
                            download_task.channel_url = uploader.url
                            download_task.channel_name = uploader.name
                            download_task.channel_avatar = uploader.avatar
                            session.add(download_task)
                            session.commit()
                            session.expunge(download_task)

                    message = Message()
                    message.body = DownloadTaskSchema().dumps(download_task)
                    session.add(message)
                    session.commit()
                    RedisMessageQueue(queue_name=constants.QUEUE_DOWNLOAD_TASK).enqueue(message)
                    message.send_status = 'SENDING'
                    session.commit()

                    logger.info(f"结束生成视频任务：channel {video.get_uploader().name}, video: {url}")

            except Exception as e:
                if url:
                    logger.error(f"处理消息时发生错误: url: {url}, {e}", exc_info=True)
                else:
                    logger.error(f"处理消息时发生错误: {e}", exc_info=True)
