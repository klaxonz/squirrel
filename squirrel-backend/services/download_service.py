import datetime
import json
import logging

from sqlalchemy import select

from common import constants
from consumer import extract_task
from core.cache import RedisClient
from core.database import get_session
from downloader.id_extractor import extract_id_from_url
from models.message import Message
from models.video import Video
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()


def start(
        url: str,
        if_only_extract: bool = True,
        if_subscribe: bool = False,
        if_retry: bool = False,
        if_manual_retry: bool = False,
        if_manual_download: bool = False,
        subscribe_id: int = None,
):
    video_id = extract_id_from_url(url)
    domain = extract_top_level_domain(url)

    client = RedisClient.get_instance().client
    key = f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}'
    if if_only_extract:
        with get_session() as session:
            video = session.execute(select(Video).where(Video.url == url)).first()
            if video:
                return

        value = client.hget(key, 'if_extract')
        if value:
            now = datetime.datetime.now().timestamp()
            if now - float(value) < 10 * 60 * 1000:
                return
    else:
        if not if_manual_retry:
            with get_session() as session:
                video = session.exec(select(Video).where(Video.id == url)).first()
                if video and video.is_downloaded:
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
            'if_manual': if_manual_retry or if_manual_download,
            'subscribe_id': subscribe_id,
        }

        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()

        dump_json = message.to_dict()
        if if_manual_retry or if_manual_download:
            extract_task.process_extract_scheduled_message.send(dump_json)
        else:
            extract_task.process_extract_message.send(dump_json)


def stop(task_id: int):
    client = RedisClient.get_instance().client
    client.set(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_STATUS}:{task_id}', 'stop')
