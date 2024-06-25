import uuid

from common.constants import QUEUE_DOWNLOAD_TASK
from common.message_queue import RedisMessageQueue
from common.url_helper import extract_top_level_domain
from downloader.id_extractor import extract_id_from_url
from model.download_task import DownloadTask
from model.message import Message


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

    message_id = str(uuid.uuid4()).replace('-', '')
    message_body = download_task.to_json()
    message = Message(
        message_id=message_id,
        body=message_body
    )
    message.save()
    RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)
    Message.update(send_status='SENDING').where(message_id=message_id, send_status='PENDING').execute()