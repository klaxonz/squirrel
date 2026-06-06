import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from common.log import init_logging
from core.config import settings
from core.database_upgrade import upgrade_database
from core.site_config_manager import apply_site_config_overrides
from core.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
    reset_startup_dependency_issues,
)
from site_runtimes.manager import bootstrap_site_runtimes, shutdown_site_runtimes
from utils.cookie import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from utils.runtime_http import set_cloudflare_bypass_client
from utils.runtime_http import set_cookie_domain_resolver, set_cookie_file_resolver

logger = logging.getLogger(__name__)

STARTUP_TOTAL_STEPS = 5
SHUTDOWN_TOTAL_STEPS = 1


def _log_lifecycle_event(phase: str, message: str) -> None:
    logger.info('%s: %s', phase, message)


def _log_lifecycle_step(phase: str, step: int, total: int, message: str) -> None:
    logger.info('%s [%s/%s] %s', phase, step, total, message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 应用生命周期管理

    启动时按顺序执行：
    1. 启动插件 runtime manager

    关闭时优雅停止所有服务
    """
    _log_lifecycle_event('Startup', 'begin')
    reset_startup_dependency_issues()

    _log_lifecycle_step('Startup', 1, STARTUP_TOTAL_STEPS, 'Applying site configuration overrides')
    try:
        apply_site_config_overrides()
    except Exception:
        logger.exception('Startup [1/%s] Failed to apply site configuration overrides', STARTUP_TOTAL_STEPS)
        raise
    _log_lifecycle_step('Startup', 1, STARTUP_TOTAL_STEPS, 'Site configuration overrides applied')

    _log_lifecycle_step('Startup', 2, STARTUP_TOTAL_STEPS, 'Configuring runtime HTTP helpers')
    runtime_http_enabled: list[str] = []
    runtime_http_degraded: list[str] = []
    try:
        from utils.cloudflare_bypass import get_default_client
        set_cloudflare_bypass_client(get_default_client())
        runtime_http_enabled.append('cloudflare_bypass')
        clear_optional_startup_issue('cloudflare_bypass')
    except Exception as exc:
        record_optional_startup_issue('cloudflare_bypass', exc)
        runtime_http_degraded.append(f'cloudflare_bypass={exc}')
    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
        runtime_http_enabled.append('cookie_resolver')
    except Exception:
        logger.exception('Startup [2/%s] Failed to configure cookie resolver', STARTUP_TOTAL_STEPS)
        raise

    if runtime_http_degraded:
        logger.warning(
            'Startup [2/%s] Runtime HTTP helpers ready with degraded features: enabled=%s degraded=%s',
            STARTUP_TOTAL_STEPS,
            ', '.join(runtime_http_enabled) if runtime_http_enabled else 'none',
            '; '.join(runtime_http_degraded),
        )
    else:
        _log_lifecycle_step('Startup', 2, STARTUP_TOTAL_STEPS, 'Runtime HTTP helpers ready')

    _log_lifecycle_step('Startup', 3, STARTUP_TOTAL_STEPS, 'Bootstrapping site runtime manager')
    try:
        from services.youtube_oauth_service import get_oauth_credentials_for_daemon
        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ['YOUTUBE_OAUTH_STATE_FILE'] = oauth_file
        bootstrap_site_runtimes()
        _log_lifecycle_step('Startup', 3, STARTUP_TOTAL_STEPS, 'Site runtime manager ready')
    except Exception:
        logger.exception('Startup [3/%s] Failed to bootstrap site runtime manager', STARTUP_TOTAL_STEPS)
        raise

    _log_lifecycle_step('Startup', 4, STARTUP_TOTAL_STEPS, 'Seeding video extraction projection')
    try:
        from services import video_extraction_projection_service
        rebuilt_count = video_extraction_projection_service.ensure_projection_seeded()
        _log_lifecycle_step(
            'Startup',
            4,
            STARTUP_TOTAL_STEPS,
            f'Video extraction projection ready (rebuilt={rebuilt_count})',
        )
    except Exception:
        logger.exception('Startup [4/%s] Failed to seed video extraction projection', STARTUP_TOTAL_STEPS)
        raise

    _log_lifecycle_step('Startup', 5, STARTUP_TOTAL_STEPS, 'Bootstrapping scheduled tasks')
    try:
        from services.scheduled_task_bootstrap import ensure_system_tasks
        ensure_system_tasks()
        clear_optional_startup_issue('scheduled_task_bootstrap')
        _log_lifecycle_step('Startup', 5, STARTUP_TOTAL_STEPS, 'Scheduled tasks ready')
    except Exception as exc:
        record_optional_startup_issue('scheduled_task_bootstrap', exc)
        logger.warning(
            'Startup [5/%s] Scheduled task bootstrap degraded: %s',
            STARTUP_TOTAL_STEPS,
            exc,
            exc_info=True,
        )

    _log_lifecycle_event('Startup', 'complete')

    yield

    _log_lifecycle_event('Shutdown', 'begin')

    _log_lifecycle_step('Shutdown', 1, SHUTDOWN_TOTAL_STEPS, 'Stopping site runtime manager')
    try:
        shutdown_site_runtimes()
        _log_lifecycle_step('Shutdown', 1, SHUTDOWN_TOTAL_STEPS, 'Site runtime manager stopped')
    except Exception as exc:
        logger.warning('Shutdown [1/%s] Error stopping site runtime manager (ignored): %s', SHUTDOWN_TOTAL_STEPS, exc)

    _log_lifecycle_event('Shutdown', 'complete')


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
    
    logger.info(
        'Launching FastAPI server host=%s port=%s mode=%s',
        '0.0.0.0',
        settings.PORT,
        'development' if settings.is_dev else 'production',
    )

    if settings.is_dev:
        uvicorn.run(
            "main:create_application",
            host="0.0.0.0",
            port=settings.PORT,
            reload=False,
            factory=True,
            log_config=None,
            access_log=False,
        )
    else:
        app = create_application()
        uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_config=None, access_log=False)


if __name__ == "__main__":
    main()


