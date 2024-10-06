from alembic.config import Config
from dotenv import load_dotenv

from alembic import command

load_dotenv(override=True)

import logging
import uvicorn
from schedule.schedule import Scheduler
from common.log import init_logging
from schedule import TaskRegistry
from consumer import ConsumerRegistry


def create_app():
    from api.base import app
    return app


logger = logging.getLogger(__name__)

consumers = []


def upgrade_database():
    alembic_cfg = Config("alembic.ini")
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


if __name__ == "__main__":
    # 初始化日志配置
    init_logging()
    # 初始化数据库
    upgrade_database()

    start_scheduler()
    start_consumers()

    # 启动服务
    logger.info('Starting server...')
    start_fastapi_server()
