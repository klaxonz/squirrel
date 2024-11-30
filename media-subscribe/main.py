import logging
import os
import threading
import dramatiq
import time
import signal
import importlib
import pkgutil
from dramatiq.worker import Worker

import uvicorn
from alembic.config import Config as AlembicConfig
from alembic import command

from common.log import init_logging
from common import constants
from core.config import settings
from schedule import TaskRegistry
from schedule.schedule import Scheduler
from consumer.base import redis_broker

logger = logging.getLogger(__name__)

def auto_discover_actors(package_name='consumer'):
    """自动发现和导入所有的 actors"""
    package = importlib.import_module(package_name)
    
    logger.info(f"Discovering actors in package: {package_name}")
    
    for _, name, _ in pkgutil.iter_modules([os.path.dirname(package.__file__)]):
        if name != 'base':  # 跳过 base.py
            module_name = f'{package_name}.{name}'
            logger.info(f"Importing module: {module_name}")
            importlib.import_module(module_name)

def create_workers():
    # 声明所有队列
    queues = [
        constants.QUEUE_SUBSCRIBE_TASK,
        constants.QUEUE_DOWNLOAD_TASK,
        constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD,
        constants.QUEUE_VIDEO_PROGRESS_TASK,
        'extract_bilibili',
        'extract_youtube',
        'extract_pornhub',
        'extract_javdb'
    ]
    
    for queue in queues:
        redis_broker.declare_queue(queue)

    logger.info(f"Broker middleware: {redis_broker.middleware}")
    logger.info(f"Target queues: {redis_broker.queues}")

    # 设置全局 broker
    dramatiq.set_broker(redis_broker)

    # 自动发现和导入 actors
    auto_discover_actors()

    # 为每个队列创建一个 worker
    workers = []
    for queue in queues:
        worker = Worker(
            redis_broker,
            queues=[queue],
            worker_threads=1,
            worker_timeout=1000,
        )
        workers.append(worker)
        logger.info(f"Created worker for queue: {queue}")

    logger.info(f"Registered actors: {redis_broker.actors}")
    return workers

def run_workers():
    workers = create_workers()
    
    def signal_handler(signum, frame):
        logger.info("Stopping workers...")
        for worker in workers:
            worker.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting workers...")
    for worker in workers:
        worker.start()

    return workers

def start_workers():
    """在新线程中启动 workers"""
    logger.info('Starting workers in background thread...')
    workers = run_workers()
    return workers

def init_app():
    """初始化应用程序"""
    # 初始化日志配置
    init_logging()

    # 使用 settings.database_url
    logger.info(f"Initializing app with DATABASE_URL: {settings.database_url}")


def create_app():
    from api.base import app
    return app


def upgrade_database():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    logger.info(f"Upgrading database with alembic.ini: {alembic_ini_path}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


def start_scheduler():
    """配置并启动定时任务调度器"""
    logger.info('Starting scheduler...')
    scheduler = Scheduler()

    for task_class in TaskRegistry.tasks:
        logger.info(f"Registering task: {task_class.__name__} with interval {task_class.interval} {task_class.unit}")
        scheduler.add_job(
            task_class.run,
            interval=task_class.interval,
            unit=task_class.unit,
            start_immediately=task_class.start_immediately
        )

    scheduler.start()
    logger.info('Scheduler started.')



def start_fastapi_server():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


def main():
    # 初始化应用
    init_app()

    # 执行数据库迁移
    upgrade_database()

    # 启动 workers
    workers = start_workers()

    # 启动调度器
    start_scheduler()

    # 启动 FastAPI 服务器
    logger.info('Starting server...')
    try:
        start_fastapi_server()
    finally:
        # 确保在程序退出时停止 workers
        logger.info("Stopping workers...")
        for worker in workers:
            worker.stop()


if __name__ == "__main__":
    main()
