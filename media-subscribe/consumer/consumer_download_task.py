import json
import logging

from playhouse.shortcuts import dict_to_model, model_to_dict

from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.download_task import DownloadTask
from utils import json_serialize

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            download_task = None
            try:
                message = self.mq.wait_and_dequeue(timeout=None)
                if message:
                    self.handle_message(message)

                    download_task = dict_to_model(DownloadTask, json.loads(message.body))
                    key = f"task:{download_task.domain}:{download_task.video_id}"

                    if self.redis.exists(key):
                        continue

                    DownloadTask.update(status='DOWNLOADING').where(
                        DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'WAITING').execute()

                    Downloader.download(download_task.url)

                    DownloadTask.update(status='COMPLETED').where(
                        DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'DOWNLOADING').execute()

                    # 写入缓存
                    self.redis.set(key, download_task.video_id, 12 * 60 * 60)

                    download_task = None
            except Exception as e:
                logger.error(
                    f"处理消息时发生错误: {e}, message: {json.dumps(model_to_dict(message), default=json_serialize.more)}",
                    exc_info=True)
                if download_task:
                    DownloadTask.update(status='FAILED', error_message=str(e)).where(
                        DownloadTask.task_id == download_task.task_id).execute()
