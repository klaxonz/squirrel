import json
import logging

import common.constants as constants
from common.database import get_session
from common.message_queue import RedisMessageQueue
from common.url_helper import extract_top_level_domain
from downloader.id_extractor import extract_id_from_url
from model.channel import ChannelVideo, Channel, ChannelVideoSchema
from model.download_task import DownloadTask, DownloadTaskSchema
from model.message import Message

logger = logging.getLogger(__name__)


def start_download(url: str):

    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)

    with get_session() as session:
        download_task = DownloadTask()
        download_task.url = url,
        download_task.domain = domain,
        download_task.video_id = video_id,
        download_task.status = "PENDING",
        session.add(download_task)
        session.commit()

        message = Message()
        message.body = DownloadTaskSchema().dumps(download_task)
        session.add(message)
        session.commit()

        RedisMessageQueue(queue_name=constants.QUEUE_EXTRACT_TASK).enqueue(message)

        session.query(Message).filter(Message.message_id == message.message_id,
                                      Message.send_status == 'PENDING').update({'send_status': 'SENDING'})

        session.commit()


def start_extract_and_download(url: str, if_only_extract: bool = True, if_subscribe: bool = False, if_retry: bool = False):

    with get_session() as session:

        content = {
            'url': url,
            'if_retry': if_retry,
            'if_subscribe': if_subscribe,
            'if_only_extract': if_only_extract
        }

        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()

        RedisMessageQueue(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD).enqueue(message)
        session.commit()


def start_extract(url: str, channel: Channel):
    if 'youtube.com' in url:
        url = "https://www.youtube.com/watch?" + url.split("?")[1]

    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)

    with get_session() as session:
        channel_video = session.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id,
                                                           ChannelVideo.video_id == video_id).first()
        if channel_video and channel_video.title is not None and channel.if_auto_download:
            if channel_video.if_downloaded:
                logger.info(f"extract task already exists: {url}")
                return

        if channel_video is None:
            channel_video = ChannelVideo()
            channel_video.channel_id = channel.channel_id,
            channel_video.channel_name = channel.name,
            channel_video.domain = domain,
            channel_video.video_id = video_id,
            channel_video.url = url,
            session.add(channel_video)
            session.commit()

        message = Message()
        message.body = ChannelVideoSchema().dumps(channel_video)
        session.add(message)
        session.commit()

        RedisMessageQueue(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT).enqueue(message)

        session.query(Message).filter(Message.message_id == message.message_id,
                                      Message.send_status == 'PENDING').update({'send_status': 'SENDING'})
        session.commit()
