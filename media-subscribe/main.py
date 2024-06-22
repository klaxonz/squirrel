# media-subscribe/main.py

import logging.config
import uvicorn
from dotenv import load_dotenv
from common.consumer import DownloadTaskConsumerThread
from common.database import DatabaseManager
from api.api import app
from model.task import Task
from common.constants import QUEUE_DOWNLOAD_TASK
from schedule.schedule import Scheduler, RetryFailedTask

load_dotenv(override=True)

# 定义日志配置字典
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG',  # 控制台日志级别
        },
        'file': {
            'class': 'logging.FileHandler',  # 如果需要记录到文件
            'filename': 'app.log',  # 日志文件名
            'formatter': 'default',
            'level': 'INFO',  # 文件日志级别
        },
    },
    'root': {  # 全局日志配置
        'handlers': ['console', 'file'],  # 同时输出到控制台和文件
        'level': 'INFO',  # 应用默认日志级别
    },
}

# 在应用启动时应用日志配置
logging.config.dictConfig(LOGGING_CONFIG)

if __name__ == "__main__":
    # 初始化数据库
    tables = [Task]
    DatabaseManager.initialize_database(tables)
    # 启动消费者
    consumer_thread = DownloadTaskConsumerThread(queue_name=QUEUE_DOWNLOAD_TASK)
    consumer_thread.start()
    # 启动定时任务
    scheduler = Scheduler()
    scheduler.add_job(RetryFailedTask.retry_failed_task, interval=1, unit='minutes')
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
