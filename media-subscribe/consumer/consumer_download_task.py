import json
import logging

from common.database import get_session
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.download_task import DownloadTaskSchema
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

                        download_task.status = 'DOWNLOADING'
                        session.commit()
                        Downloader.download(download_task.url)
                        download_task.status = 'COMPLETED'
                        download_task.error_message = ''
                        session.commit()

                        download_task = None
                except Exception as e:
                    logger.error(
                        f"处理消息时发生错误: {e}, message: {MessageSchema().dumps(message)}",
                        exc_info=True)
                    if download_task:
                        download_task.status = 'FAILED'
                        download_task.error_message = str(e)
                        session.commit()
