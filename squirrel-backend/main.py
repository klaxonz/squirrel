import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from alembic import command
from common.log import init_logging
from core.config import settings
from core.site_config_manager import apply_site_config_overrides
from plugins.loader import init_plugins, app_start, app_stop

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
    2. 初始化队列配置
    3. 触发插件启动钩子

    关闭时优雅停止所有服务
    """
    # ========== 启动阶段 ==========
    logger.info("=" * 60)
    logger.info("Application startup sequence begin")
    logger.info("=" * 60)
    
    # 0. 应用站点配置覆盖（HTTP / 代理 / 限流 等）
    logger.info("[0/5] Applying site configuration overrides...")
    try:
        apply_site_config_overrides()
        logger.info("[0/5] ✓ Site configuration overrides applied")
    except Exception as e:
        logger.warning(f"[0/5] ⚠ Failed to apply site config overrides: {e}")

    # 1. 加载插件（必须先加载，注册到 SDK 注册表）
    logger.info("[1/4] Loading plugins...")
    try:
        init_plugins()
        logger.info("[1/4] ✓ Plugins loaded")
    except Exception as e:
        logger.exception(f"[1/4] ✗ Failed to load plugins: {e}")
        raise

    # 2. 初始化队列配置（基于插件注册表）
    logger.info("[2/4] Initializing queue configuration...")
    try:
        from mq.queue_config import ensure_queue_config_initialized
        ensure_queue_config_initialized()
        logger.info("[2/4] ✓ Queue configuration initialized")
    except Exception as e:
        logger.exception(f"[2/4] ✗ Failed to initialize queue config: {e}")
        raise

    # 3. 触发插件启动钩子
    logger.info("[3/4] Triggering plugin startup hooks...")
    try:
        app_start()
        logger.info("[3/4] ✓ Plugin startup hooks completed")
    except Exception as e:
        logger.warning(f"[3/4] ⚠ Plugin startup hooks failed (ignored): {e}")
    

    logger.info("=" * 60)
    logger.info("✓ Application startup completed successfully")
    logger.info("=" * 60)
    
    yield
    
    # ========== 关闭阶段 ==========
    logger.info("=" * 60)
    logger.info("Application shutdown sequence begin")
    logger.info("=" * 60)
    
    # 优雅停止所有服务（逆序）
    logger.info("[2/3] Stopping plugins...")
    try:
        app_stop()
        logger.info("[2/3] ✓ Plugins stopped")
    except Exception as e:
        logger.warning(f"[2/3] ⚠ Error stopping plugins (ignored): {e}")

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
