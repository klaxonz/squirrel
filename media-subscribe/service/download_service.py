import json

from playhouse.shortcuts import model_to_dict

from common.constants import QUEUE_EXTRACT_TASK
from common.message_queue import RedisMessageQueue
from common.url_helper import extract_top_level_domain
from downloader.id_extractor import extract_id_from_url
from model.download_task import DownloadTask
from model.message import Message
from utils import json_serialize


def start_download(url: str):
    if 'youtube.com' in url:
        url = "https://www.youtube.com/watch?" + url.split("?")[1]

    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)

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
