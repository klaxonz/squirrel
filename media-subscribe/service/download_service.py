import json

from playhouse.shortcuts import model_to_dict

from common.cache import RedisClient
from common.constants import QUEUE_EXTRACT_TASK, QUEUE_CHANNEL_VIDEO_UPDATE
from common.message_queue import RedisMessageQueue
from common.url_helper import extract_top_level_domain
from downloader.id_extractor import extract_id_from_url
from model.channel import ChannelVideo, Channel
from model.download_task import DownloadTask
from model.message import Message
from utils import json_serialize


def start_download(url: str):
    if 'youtube.com' in url:
        url = "https://www.youtube.com/watch?" + url.split("?")[1]

    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)

    client = RedisClient.get_instance().client
    key = f"task:{domain}:{video_id}"

    if client.exists(key):
        return

    download_task = DownloadTask(
        url=url,
        domain=domain,
        video_id=video_id,
        status="PENDING",
    )
    download_task.save()

    message = Message(
        body=json.dumps(model_to_dict(download_task), default=json_serialize.more)
    )
    message.save()

    RedisMessageQueue(queue_name=QUEUE_EXTRACT_TASK).enqueue(message)
    Message.update(send_status='SENDING').where(Message.message_id == message.message_id,
                                                Message.send_status == 'PENDING').execute()


def start_extract(url: str, channel: Channel):
    if 'youtube.com' in url:
        url = "https://www.youtube.com/watch?" + url.split("?")[1]

    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)

    client = RedisClient.get_instance().client
    key = f"task:extract:{domain}:{channel.channel_id}:{video_id}"

    if client.exists(key):
        return

    channel_video = ChannelVideo(
        channel_id=channel.channel_id,
        channel_name=channel.name,
        domain=domain,
        video_id=video_id,
        url=url,
    )
    channel_video.save()

    message = Message(
        body=json.dumps(model_to_dict(channel_video), default=json_serialize.more)
    )
    message.save()

    RedisMessageQueue(queue_name=QUEUE_CHANNEL_VIDEO_UPDATE).enqueue(message)
    Message.update(send_status='SENDING').where(Message.message_id == message.message_id,
                                                Message.send_status == 'PENDING').execute()

