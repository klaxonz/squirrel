import datetime
import json
import logging

from sqlmodel import select

from common import constants
from core.cache import RedisClient
from core.database import get_session
from utils.url_helper import extract_top_level_domain
from downloader.id_extractor import extract_id_from_url
from model.channel import ChannelVideo
from model.message import Message
from consumer import extract_task

logger = logging.getLogger()


def start(url: str, if_only_extract: bool = True, if_subscribe: bool = False, if_retry: bool = False,
          if_manual_retry: bool = False, if_manual_download: bool = False):
    video_id = extract_id_from_url(url)
    domain = extract_top_level_domain(url)

    client = RedisClient.get_instance().client
    key = f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}'
    if if_only_extract:
        with get_session() as session:
            channel_video = session.query(ChannelVideo).filter(ChannelVideo.domain == domain,
                                                               ChannelVideo.video_id == video_id).first()
            if channel_video:
                return

        value = client.hget(key, 'if_extract')
        if value:
            now = datetime.datetime.now().timestamp()
            if now - float(value) < 10 * 60 * 1000:
                return
    else:
        if not if_manual_retry:
            with get_session() as session:
                channel_video = session.query(ChannelVideo).filter(ChannelVideo.domain == domain,
                                                                   ChannelVideo.video_id == video_id).first()
                if channel_video and channel_video.if_downloaded:
                    return
            value = client.hget(key, 'if_download')
            if value:
                now = datetime.datetime.now().timestamp()
                if now - float(value) < 10 * 60 * 1000:
                    return

    with get_session() as session:
        content = {
            'url': url,
            'if_retry': if_retry,
            'if_subscribe': if_subscribe,
            'if_only_extract': if_only_extract,
            'if_manual_retry': if_manual_retry,
            'if_manual_download': if_manual_download,
            'if_manual': if_manual_retry or if_manual_download
        }

        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()

        message = session.exec(select(Message).where(Message.message_id == message.message_id)).first()
        dump_json = message.model_dump_json()
        if if_manual_retry or if_manual_download:
            extract_task.process_extract_scheduled_message.send(dump_json)
        else:
            extract_task.process_extract_message.send(dump_json)


def stop(task_id: int):
    client = RedisClient.get_instance().client
    client.set(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_STATUS}:{task_id}', 'stop')
