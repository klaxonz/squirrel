# media-subscribe/main.py

import logging
import uvicorn
from dotenv import load_dotenv
from common.consumer import DownloadTaskConsumerThread
from common.database import DatabaseManager
from api.api import app
from common.constants import QUEUE_DOWNLOAD_TASK
from schedule.schedule import Scheduler, RetryFailedTask

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    # 初始化数据库
    DatabaseManager.initialize_database()
    # 启动消费者
    consumer_thread = DownloadTaskConsumerThread(queue_name=QUEUE_DOWNLOAD_TASK)
    consumer_thread.start()
    # 启动定时任务
    scheduler = Scheduler()
    scheduler.add_job(RetryFailedTask.retry_failed_task, interval=1, unit='minutes')
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)