import importlib
import logging
import os
import pkgutil
import signal

import dramatiq
import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig
from dramatiq.worker import Worker

from common import constants
from common.log import init_logging
from consumer.base import redis_broker
from schedule import TaskRegistry
from schedule.schedule import Scheduler

logger = logging.getLogger(__name__)


def auto_discover_actors(package_name='consumer'):
    """自动发现和导入所有的 actors"""
    package = importlib.import_module(package_name)

    logger.info(f"Discovering actors in package: {package_name}")

    for _, name, _ in pkgutil.iter_modules([os.path.dirname(package.__file__)]):
        if name != 'base':
            module_name = f'{package_name}.{name}'
            logger.info(f"Importing module: {module_name}")
            importlib.import_module(module_name)


def create_workers():
    queues = [
        constants.QUEUE_VIDEO_DOWNLOAD_TASK,
        constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_TASK,
        constants.QUEUE_VIDEO_EXTRACT_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_BILIBILI_TASK,
        constants.QUEUE_VIDEO_EXTRACT_BILIBILI_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_TASK,
        constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_PORNHUB_TASK,
        constants.QUEUE_VIDEO_EXTRACT_PORNHUB_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_EXTRACT_JAVDB_TASK,
        constants.QUEUE_VIDEO_EXTRACT_JAVDB_SCHEDULED_TASK,
        constants.QUEUE_VIDEO_DOWNLOAD_TASK,
        constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED_TASK,
        constants.QUEUE_SUBSCRIBE_TASK,
        constants.QUEUE_VIDEO_PROGRESS_TASK,
    ]

    for queue in queues:
        redis_broker.declare_queue(queue)

    dramatiq.set_broker(redis_broker)

    auto_discover_actors()

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
    logger.info('Starting workers in background thread...')
    workers = run_workers()
    return workers


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
    # 执行数据库迁移
    upgrade_database()
    
    init_logging()

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
