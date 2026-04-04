import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from common.log import init_logging
from core.config import settings
from core.database_upgrade import upgrade_database
from core.site_config_manager import apply_site_config_overrides
from plugins.manager import bootstrap_plugin_runtime, shutdown_plugin_runtime
from utils.cookie import resolve_cookie_file_for_url
from utils.runtime_http import set_cloudflare_bypass_client
from utils.runtime_http import set_cookie_file_resolver

logger = logging.getLogger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 应用生命周期管理

    启动时按顺序执行：
    1. 启动插件 runtime manager

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

    # 0.5. 配置 Cloudflare bypass 客户端
    logger.info("[0.5/5] Configuring Cloudflare bypass client...")
    try:
        from utils.cloudflare_bypass import get_default_client
        set_cloudflare_bypass_client(get_default_client())
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        logger.info("[0.5/5] ✓ Cloudflare bypass client configured")
    except Exception as e:
        logger.warning(f"[0.5/5] ⚠ Failed to configure Cloudflare bypass client: {e}")

    # 1. 启动插件 runtime manager
    logger.info("[1/4] Bootstrapping plugin runtime manager...")
    try:
        bootstrap_plugin_runtime()
        logger.info("[1/4] ✓ Plugin runtime manager bootstrapped")
    except Exception as e:
        logger.exception(f"[1/4] ✗ Failed to bootstrap plugin runtime manager: {e}")
        raise

    logger.info("[2/4] Seeding video extraction projection...")
    try:
        from services import video_extraction_projection_service
        rebuilt_count = video_extraction_projection_service.ensure_projection_seeded()
        logger.info(f"[2/4] ✓ Video extraction projection ready (rebuilt={rebuilt_count})")
    except Exception as e:
        logger.exception(f"[2/4] ✗ Failed to seed video extraction projection: {e}")
        raise

    logger.info("=" * 60)
    logger.info("✓ Application startup completed successfully")
    logger.info("=" * 60)
    
    yield
    
    # ========== 关闭阶段 ==========
    logger.info("=" * 60)
    logger.info("Application shutdown sequence begin")
    logger.info("=" * 60)
    
    # 优雅停止所有服务（逆序）
    logger.info("[2/3] Stopping plugin runtime manager...")
    try:
        shutdown_plugin_runtime()
        logger.info("[2/3] ✓ Plugin runtime manager stopped")
    except Exception as e:
        logger.warning(f"[2/3] ⚠ Error stopping plugin runtime manager (ignored): {e}")

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
