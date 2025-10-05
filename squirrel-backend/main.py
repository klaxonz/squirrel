import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from common.constants import SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER
from common.log import init_logging
from controllers.scheduler_controller import scheduler_start, scheduler_stop
from controllers.worker_controller import worker_start, worker_stop
from core.config import settings
from core.extraction import initialize_plugin_bridge
from plugins.loader import init_plugins, app_start, app_stop
from services.system_config_service import get_bool

logger = logging.getLogger()


def upgrade_database() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")
    logger.info(f"Upgrading database with alembic.ini: {alembic_ini_path}")
    alembic_cfg = AlembicConfig(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 应用生命周期管理
    
    启动时按顺序执行：
    1. 加载插件（注册到 SDK 注册表）
    2. 初始化插件桥接器（同步插件到后端提取器工厂）
    3. 触发插件启动钩子
    4. 启动消息队列 Worker
    5. 启动任务调度器
    
    关闭时优雅停止所有服务
    """
    # ========== 启动阶段 ==========
    logger.info("=" * 60)
    logger.info("Application startup sequence begin")
    logger.info("=" * 60)
    
    # 1. 加载插件（必须先加载，注册到 SDK 注册表）
    logger.info("[1/5] Loading plugins...")
    try:
        init_plugins()
        logger.info("[1/5] ✓ Plugins loaded")
    except Exception as e:
        logger.exception(f"[1/5] ✗ Failed to load plugins: {e}")
        raise
    
    # 2. 初始化插件桥接器（从 SDK 注册表同步到后端工厂）
    logger.info("[2/5] Initializing plugin bridge...")
    try:
        initialize_plugin_bridge()
        logger.info("[2/5] ✓ Plugin bridge initialized")
    except Exception as e:
        logger.exception(f"[2/5] ✗ Failed to initialize plugin bridge: {e}")
        raise
    
    # 2.1 初始化队列配置（基于插件注册表）
    logger.info("[2.1/5] Initializing queue configuration...")
    try:
        from mq.queue_config import ensure_queue_config_initialized
        ensure_queue_config_initialized()
        logger.info("[2.1/5] ✓ Queue configuration initialized")
    except Exception as e:
        logger.exception(f"[2.1/5] ✗ Failed to initialize queue config: {e}")
        raise
    
    # 2.2 初始化进度跟踪监听器
    logger.info("[2.2/5] Setting up progress listeners...")
    try:
        from core.progress import setup_default_listeners
        setup_default_listeners()
        logger.info("[2.2/5] ✓ Progress listeners setup completed")
    except Exception as e:
        logger.warning(f"[2.2/5] ⚠ Failed to setup progress listeners (ignored): {e}")
    
    # 3. 触发插件启动钩子
    logger.info("[3/5] Triggering plugin startup hooks...")
    try:
        app_start()
        logger.info("[3/5] ✓ Plugin startup hooks completed")
    except Exception as e:
        logger.warning(f"[3/5] ⚠ Plugin startup hooks failed (ignored): {e}")
    
    # 4. 启动 Worker
    enable_worker = get_bool(SYS_ENABLE_WORKER, True)
    if enable_worker:
        logger.info("[4/5] Starting message queue worker...")
        try:
            worker_start()
            logger.info("[4/5] ✓ Worker started")
        except Exception as e:
            logger.exception(f"[4/5] ✗ Failed to start worker: {e}")
            raise
    else:
        logger.info("[4/5] ⊘ Worker disabled by system config")
    
    # 5. 启动调度器
    enable_scheduler = get_bool(SYS_ENABLE_SCHEDULER, True)
    if enable_scheduler:
        logger.info("[5/5] Starting task scheduler...")
        try:
            scheduler_start()
            logger.info("[5/5] ✓ Scheduler started")
        except Exception as e:
            logger.exception(f"[5/5] ✗ Failed to start scheduler: {e}")
            raise
    else:
        logger.info("[5/5] ⊘ Scheduler disabled by system config")
    
    logger.info("=" * 60)
    logger.info("✓ Application startup completed successfully")
    logger.info("=" * 60)
    
    yield
    
    # ========== 关闭阶段 ==========
    logger.info("=" * 60)
    logger.info("Application shutdown sequence begin")
    logger.info("=" * 60)
    
    # 优雅停止所有服务（逆序）
    logger.info("[1/3] Stopping scheduler...")
    try:
        scheduler_stop()
        logger.info("[1/3] ✓ Scheduler stopped")
    except Exception as e:
        logger.warning(f"[1/3] ⚠ Error stopping scheduler (ignored): {e}")
    
    logger.info("[2/3] Stopping plugins...")
    try:
        app_stop()
        logger.info("[2/3] ✓ Plugins stopped")
    except Exception as e:
        logger.warning(f"[2/3] ⚠ Error stopping plugins (ignored): {e}")
    
    logger.info("[3/3] Stopping worker...")
    try:
        worker_stop()
        logger.info("[3/3] ✓ Worker stopped")
    except Exception as e:
        logger.warning(f"[3/3] ⚠ Error stopping worker (ignored): {e}")
    
    logger.info("=" * 60)
    logger.info("✓ Application shutdown completed")
    logger.info("=" * 60)


def create_application() -> FastAPI:
    """
    创建 FastAPI 应用实例并绑定生命周期管理
    
    Returns:
        配置好的 FastAPI 应用实例
    """
    from routes.base import create_app
    
    # 创建应用实例并注入生命周期管理
    app = create_app()
    app.router.lifespan_context = lifespan
    
    return app


def main() -> None:
    """
    应用程序主入口函数
    
    执行流程：
    1. 升级数据库
    2. 初始化日志系统
    3. 创建 FastAPI 应用（包含生命周期管理）
    4. 启动服务器
    """
    # 预初始化步骤
    upgrade_database()
    init_logging()
    
    # 创建应用
    app = create_application()
    
    # 启动服务器
    logger.info("Starting FastAPI server...")
    if settings.is_dev:
        uvicorn.run(
            "main:create_application",
            host="0.0.0.0",
            port=8000,
            reload=False,
            factory=True
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
