import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from application.runtime_setup import (
    apply_site_config,
    bootstrap_site_runtimes_with_oauth,
    configure_runtime_http,
)
from infrastructure.config.settings import settings
from infrastructure.config.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
    reset_startup_dependency_issues,
)
from infrastructure.database.migrations import upgrade_database
from infrastructure.site_runtimes.manager import shutdown_site_runtimes
from shared_kernel.infrastructure.log import init_logging

logger = logging.getLogger(__name__)

STARTUP_TOTAL_STEPS = 5
SHUTDOWN_TOTAL_STEPS = 1


def _log_lifecycle_event(phase: str, message: str) -> None:
    logger.info("%s: %s", phase, message)


def _log_lifecycle_step(phase: str, step: int, total: int, message: str) -> None:
    logger.info("%s [%s/%s] %s", phase, step, total, message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI application lifecycle management.

    Executes in order on startup:
    1. Start the plugin runtime manager

    Gracefully stops all services on shutdown
    """
    _log_lifecycle_event("Startup", "begin")
    reset_startup_dependency_issues()

    _log_lifecycle_step("Startup", 1, STARTUP_TOTAL_STEPS, "Applying site configuration overrides")
    apply_site_config()
    _log_lifecycle_step("Startup", 1, STARTUP_TOTAL_STEPS, "Site configuration overrides applied")

    _log_lifecycle_step("Startup", 2, STARTUP_TOTAL_STEPS, "Configuring runtime HTTP helpers")
    configure_runtime_http()
    _log_lifecycle_step("Startup", 2, STARTUP_TOTAL_STEPS, "Runtime HTTP helpers ready")

    _log_lifecycle_step("Startup", 3, STARTUP_TOTAL_STEPS, "Bootstrapping site runtime manager")
    bootstrap_site_runtimes_with_oauth()
    _log_lifecycle_step("Startup", 3, STARTUP_TOTAL_STEPS, "Site runtime manager ready")

    _log_lifecycle_step("Startup", 4, STARTUP_TOTAL_STEPS, "Bootstrapping scheduled tasks")
    try:
        from infrastructure.scheduling.bootstrap import ensure_system_tasks
        ensure_system_tasks()
        clear_optional_startup_issue("scheduled_task_bootstrap")
        _log_lifecycle_step("Startup", 4, STARTUP_TOTAL_STEPS, "Scheduled tasks ready")
    except Exception as exc:  # startup/shutdown boundary -- prevent crash during lifecycle
        record_optional_startup_issue("scheduled_task_bootstrap", exc)
        logger.warning(
            "Startup [5/%s] Scheduled task bootstrap degraded: %s",
            STARTUP_TOTAL_STEPS,
            exc,
            exc_info=True,
        )

    _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Ensuring Meilisearch index")
    if settings.MEILISEARCH_URL:
        # Meili 是搜索功能的强依赖；索引未就绪会导致 domain 过滤报错和召回异常，
        # 故失败直接终止启动。未配置 MEILISEARCH_URL 时跳过（搜索功能不可用，但浏览/详情正常）。
        try:
            from infrastructure.search.meili import ensure_videos_index
            ensure_videos_index()
            # 预热 MeiliVideoIndexer 单例（建立 client/index 对象），避免首个请求的初始化开销
            from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
            get_meili_video_indexer()
            _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Meilisearch index ready")
        except Exception:  # startup/shutdown boundary -- fail-fast on missing Meilisearch
            logger.exception("Startup [5/%s] Failed to ensure Meilisearch index", STARTUP_TOTAL_STEPS)
            raise
    else:
        logger.warning("Startup [5/%s] MEILISEARCH_URL not configured -- search disabled", STARTUP_TOTAL_STEPS)
        _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Meilisearch skipped (MEILISEARCH_URL not set)")

    _log_lifecycle_event("Startup", "complete")

    yield

    _log_lifecycle_event("Shutdown", "begin")

    _log_lifecycle_step("Shutdown", 1, SHUTDOWN_TOTAL_STEPS, "Stopping site runtime manager")
    try:
        shutdown_site_runtimes()
        _log_lifecycle_step("Shutdown", 1, SHUTDOWN_TOTAL_STEPS, "Site runtime manager stopped")
    except Exception as exc:  # cleanup during shutdown -- must not propagate
        logger.warning("Shutdown [1/%s] Error stopping site runtime manager (ignored): %s", SHUTDOWN_TOTAL_STEPS, exc)

    _log_lifecycle_event("Shutdown", "complete")


def create_application() -> FastAPI:
    """Create a FastAPI application instance with lifecycle management

    Returns:
        Configured FastAPI application instance

    """
    from application.app import create_app

    # Create application instance and inject lifecycle management
    app = create_app()
    app.router.lifespan_context = lifespan

    return app


def main() -> None:
    """Application main entry point

    Execution flow:
    1. Upgrade database
    2. Initialize logging system
    3. Create FastAPI application (with lifecycle management)
    4. Start server
    """
    # Pre-initialization steps
    upgrade_database()
    init_logging()

    logger.info(
        "Launching FastAPI server host=%s port=%s mode=%s",
        "0.0.0.0",
        settings.PORT,
        "development" if settings.is_dev else "production",
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


