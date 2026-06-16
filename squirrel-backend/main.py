import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from application.runtime_setup import (
    apply_site_config,
    configure_cloudflare_bypass,
    configure_cookie_resolvers,
    prepare_youtube_oauth_env,
    start_site_runtimes,
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
    """FastAPI application lifecycle: bootstrap runtime, serve, then shut down."""
    _log_lifecycle_event("Startup", "begin")
    reset_startup_dependency_issues()

    # 1. Site config (hard dependency)
    _log_lifecycle_step("Startup", 1, STARTUP_TOTAL_STEPS, "Applying site configuration overrides")
    try:
        apply_site_config()
    except Exception:
        logger.exception("Startup [1/%s] Failed to apply site configuration overrides", STARTUP_TOTAL_STEPS)
        raise

    # 2. Runtime HTTP: cloudflare bypass is optional (degrade), cookie resolver is required
    _log_lifecycle_step("Startup", 2, STARTUP_TOTAL_STEPS, "Configuring runtime HTTP helpers")
    try:
        configure_cloudflare_bypass()
        clear_optional_startup_issue("cloudflare_bypass")
    except Exception as exc:
        record_optional_startup_issue("cloudflare_bypass", exc)
        logger.warning("Startup [2/%s] Cloudflare bypass disabled: %s", STARTUP_TOTAL_STEPS, exc)
    try:
        configure_cookie_resolvers()
    except Exception:
        logger.exception("Startup [2/%s] Failed to configure cookie resolver", STARTUP_TOTAL_STEPS)
        raise

    # 3. Site runtimes (hard dependency) — YouTube OAuth env must be set before bootstrap
    _log_lifecycle_step("Startup", 3, STARTUP_TOTAL_STEPS, "Bootstrapping site runtime manager")
    try:
        prepare_youtube_oauth_env()
        start_site_runtimes()
    except Exception:
        logger.exception("Startup [3/%s] Failed to bootstrap site runtime manager", STARTUP_TOTAL_STEPS)
        raise

    # 4. Scheduled tasks (degraded-tolerant)
    _log_lifecycle_step("Startup", 4, STARTUP_TOTAL_STEPS, "Bootstrapping scheduled tasks")
    try:
        from infrastructure.scheduling.bootstrap import ensure_system_tasks
        ensure_system_tasks()
        clear_optional_startup_issue("scheduled_task_bootstrap")
    except Exception as exc:
        record_optional_startup_issue("scheduled_task_bootstrap", exc)
        logger.warning("Startup [4/%s] Scheduled task bootstrap degraded: %s", STARTUP_TOTAL_STEPS, exc, exc_info=True)

    # 5. Meilisearch index (hard dependency when configured; skipped if MEILISEARCH_URL unset)
    _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Ensuring Meilisearch index")
    if settings.MEILISEARCH_URL:
        try:
            from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
            from infrastructure.search.meili import ensure_videos_index
            ensure_videos_index()
            get_meili_video_indexer()  # 预热单例，避免首个请求的初始化开销
        except Exception:
            logger.exception("Startup [5/%s] Failed to ensure Meilisearch index", STARTUP_TOTAL_STEPS)
            raise
    else:
        logger.warning("Startup [5/%s] MEILISEARCH_URL not configured -- search disabled", STARTUP_TOTAL_STEPS)

    _log_lifecycle_event("Startup", "complete")

    yield

    _log_lifecycle_event("Shutdown", "begin")
    try:
        shutdown_site_runtimes()
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


