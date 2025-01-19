import logging
import os
import signal

import dramatiq
import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig
from dramatiq.worker import Worker

from common import constants
from common.global_config import IS_DEV
from common.log import init_logging
from consumer.base import redis_broker
from routes.base import app
from schedule.schedule import Scheduler
from schedule.tasks import TaskRegistry
from utils.auto_import import ModuleImporter

logger = logging.getLogger()


def create_workers():
    workers = []
    for queue in constants.get_all_queues():
        redis_broker.declare_queue(queue)
        worker = Worker(
            redis_broker,
            queues=[queue],
            worker_threads=1,
            worker_timeout=1000,
        )
        workers.append(worker)
        logger.info(f"Created worker for queue: {queue}")
    logger.info(f"Registered actors: {redis_broker.actors}")
    dramatiq.set_broker(redis_broker)
    ModuleImporter.import_classes(directory="consumer")

    return workers


def run_workers():

    def signal_handler(signum, frame):
        logger.info("Stopping workers...")
        for worker in workers:
            worker.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting workers...")
    workers = create_workers()
    for worker in workers:
        worker.start()

    return workers


def start_workers():
    logger.info('Starting workers in background thread...')
    workers = run_workers()
    return workers


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
    if IS_DEV:
        uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
    else:
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
