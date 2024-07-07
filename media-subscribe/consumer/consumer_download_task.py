import json
import logging

from common.database import get_session
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.download_task import DownloadTask, DownloadTaskSchema
from model.message import MessageSchema

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            download_task = None
            with get_session() as session:
                try:
                    message = self.mq.wait_and_dequeue(session=session, timeout=None)
                    if message:
                        self.handle_message(message, session)
                        download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)

                        session.query(DownloadTask).filter(DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'WAITING').update({'status': 'DOWNLOADING'})
                        session.commit()
                        Downloader.download(download_task.url)
                        session.query(DownloadTask).filter(DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'DOWNLOADING').update({'status': 'COMPLETED'})
                        session.commit()

                        download_task = None
                except Exception as e:
                    logger.error(
                        f"处理消息时发生错误: {e}, message: {MessageSchema().dumps(message)}",
                        exc_info=True)
                    if download_task:
                        session.query(DownloadTask).filter(DownloadTask.task_id == download_task.task_id).update({'status': 'FAILED'})
