from dotenv import load_dotenv

load_dotenv(override=True)
import logging.config
import os
import uvicorn
from api.api import app
from common.constants import QUEUE_DOWNLOAD_TASK, QUEUE_SUBSCRIBE_TASK
from common.consumer import DownloadTaskConsumerThread, SubscribeChannelConsumerThread
from common.database import DatabaseManager
from model.task import Task
from model.channel import Channel
from schedule.schedule import Scheduler, RetryFailedTask, AutoUpdateChannelVideoTask

# 定义日志配置字典
current_dir = os.path.dirname(os.getcwd())
LOG_DIR = os.path.join(current_dir, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

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
            'filename': os.path.join(LOG_DIR, 'app.log'),  # 日志文件名
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
    tables = [Task, Channel]
    DatabaseManager.initialize_database(tables)
    # 启动消费者
    download_consumer = DownloadTaskConsumerThread(queue_name=QUEUE_DOWNLOAD_TASK)
    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=QUEUE_SUBSCRIBE_TASK)
    download_consumer.start()
    subscribe_consumer.start()
    # 启动定时任务
    scheduler = Scheduler()
    scheduler.add_job(RetryFailedTask.run, interval=1, unit='minutes')
    scheduler.add_job(AutoUpdateChannelVideoTask.run, interval=2, unit='minutes')
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
