import logging

import uvicorn
from alembic.config import Config as AlembicConfig

from alembic import command
from common.log import init_logging
from consumer.decorators import ConsumerRegistry
from core.config import settings
from schedule import TaskRegistry
from schedule.schedule import Scheduler

logger = logging.getLogger(__name__)

consumers = []


def init_app():
    """初始化应用程序"""
    # 初始化日志配置
    init_logging()

    # 初始化数据库
    upgrade_database()

    # 使用 settings.database_url
    logger.info(f"Initializing app with DATABASE_URL: {settings.database_url}")


def create_app():
    from api.base import app
    return app


def upgrade_database():
    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def start_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    global consumers

    # Stop existing consumers
    for consumer in consumers:
        consumer.stop()

    consumers = []
    for consumer_class in ConsumerRegistry.consumers:
        queue_name = consumer_class.queue_name
        num_threads = consumer_class.num_threads
        for idx in range(num_threads):
            consumer = consumer_class(queue_name=queue_name, thread_id=idx)
            consumers.append(consumer)
            consumer.start()

    logger.info(f'Consumers started. Total consumers: {len(consumers)}')


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


def restart_consumers():
    global consumers

    # Stop existing consumers
    for consumer in consumers:
        consumer.stop()

    # Clear existing consumers
    consumers.clear()

    # Start new consumers
    start_consumers()


def start_fastapi_server():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


def main():
    # 初始化应用
    init_app()

    # 启动调度器
    start_scheduler()

    # 启动消费者
    start_consumers()

    # 启动 FastAPI 服务器
    logger.info('Starting server...')
    start_fastapi_server()


if __name__ == "__main__":
    main()
