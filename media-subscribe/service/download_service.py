import uuid

from common.constants import MESSAGE_TYPE_DOWNLOAD, QUEUE_DOWNLOAD_TASK
from common.message_queue import Message, RedisMessageQueue
from model.task import Task


def start_download(url: str):
    task_id = str(uuid.uuid4()).replace('-', '')
    task = {
        "url": url,
        "task_id": task_id,
        "task_type": MESSAGE_TYPE_DOWNLOAD,
    }

    Task.create_task(task)
    message = Message(task, task_id)
    RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)