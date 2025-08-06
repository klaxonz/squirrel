import asyncio
import atexit
import logging
import os
import signal
import sys

import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig

from common.global_config import IS_DEV
from common.log import init_logging
from routes.base import app
from controllers.scheduler_controller import scheduler_start, scheduler_stop
from controllers.worker_controller import worker_start, worker_stop
from services.system_config_service import get_bool
from common.constants import SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER
from proxy import initialize_proxy_system, shutdown_proxy_system

logger = logging.getLogger()


def upgrade_database():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    logger.info(f"Upgrading database with alembic.ini: {alembic_ini_path}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


def start_fastapi_server():
    if IS_DEV:
        uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


async def initialize_systems():
    """初始化所有系统组件"""
    logger.info("Initializing proxy system...")
    await initialize_proxy_system()
    logger.info("Proxy system initialized")


async def cleanup_systems():
    """清理所有系统组件"""
    logger.info("Shutting down proxy system...")
    await shutdown_proxy_system()
    logger.info("Proxy system shut down")


def register_cleanup_handlers():
    """注册清理处理器"""
    def cleanup_handler():
        try:
            asyncio.run(cleanup_systems())
        except Exception:
            logger.exception("Error during cleanup (ignored)")

    # 注册退出时的清理
    atexit.register(cleanup_handler)

    # 注册信号处理器
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        cleanup_handler()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    upgrade_database()
    init_logging()

    # 注册清理处理器
    register_cleanup_handlers()

    # 初始化代理系统
    asyncio.run(initialize_systems())

    enable_worker = get_bool(SYS_ENABLE_WORKER, True)
    enable_scheduler = get_bool(SYS_ENABLE_SCHEDULER, True)
    if enable_worker:
        worker_start()
    else:
        logger.info("Worker disabled by system config")

    if enable_scheduler:
        scheduler_start()
    else:
        logger.info("Scheduler disabled by system config")

    logger.info('Starting server...')
    try:
        start_fastapi_server()
    finally:
        # graceful stop
        try:
            scheduler_stop()
        except Exception:
            logger.exception("Error when stopping scheduler (ignored)")
        try:
            worker_stop()
        except Exception:
            logger.exception("Error when stopping workers (ignored)")
        try:
            asyncio.run(cleanup_systems())
        except Exception:
            logger.exception("Error when shutting down proxy system (ignored)")


if __name__ == "__main__":
    main()
