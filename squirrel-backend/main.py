import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from infrastructure.config.settings import settings
from infrastructure.config.site_config_manager import apply_site_config_overrides
from infrastructure.config.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
    reset_startup_dependency_issues,
)
from infrastructure.database.migrations import upgrade_database
from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from infrastructure.site_catalog.runtime_http import (
    set_cloudflare_bypass_client,
    set_cookie_domain_resolver,
    set_cookie_file_resolver,
)
from infrastructure.site_runtimes.manager import bootstrap_site_runtimes, shutdown_site_runtimes
from shared_kernel.infrastructure.log import init_logging

logger = logging.getLogger(__name__)

STARTUP_TOTAL_STEPS = 6
SHUTDOWN_TOTAL_STEPS = 1


def _log_lifecycle_event(phase: str, message: str) -> None:
    logger.info("%s: %s", phase, message)


def _log_lifecycle_step(phase: str, step: int, total: int, message: str) -> None:
    logger.info("%s [%s/%s] %s", phase, step, total, message)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI application lifecycle management

    Executes in order on startup:
    1. Start the plugin runtime manager

    Gracefully stops all services on shutdown
    """
    _log_lifecycle_event("Startup", "begin")
    reset_startup_dependency_issues()

    _log_lifecycle_step("Startup", 1, STARTUP_TOTAL_STEPS, "Applying site configuration overrides")
    try:
        apply_site_config_overrides()
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("Startup [1/%s] Failed to apply site configuration overrides", STARTUP_TOTAL_STEPS)
        raise
    _log_lifecycle_step("Startup", 1, STARTUP_TOTAL_STEPS, "Site configuration overrides applied")

    _log_lifecycle_step("Startup", 2, STARTUP_TOTAL_STEPS, "Configuring runtime HTTP helpers")
    runtime_http_enabled: list[str] = []
    runtime_http_degraded: list[str] = []
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client
        set_cloudflare_bypass_client(get_default_client())
        runtime_http_enabled.append("cloudflare_bypass")
        clear_optional_startup_issue("cloudflare_bypass")
    except Exception as exc:  # startup/shutdown boundary -- prevent crash during lifecycle
        record_optional_startup_issue("cloudflare_bypass", exc)
        runtime_http_degraded.append(f"cloudflare_bypass={exc}")
    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
        runtime_http_enabled.append("cookie_resolver")
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("Startup [2/%s] Failed to configure cookie resolver", STARTUP_TOTAL_STEPS)
        raise

    if runtime_http_degraded:
        logger.warning(
            "Startup [2/%s] Runtime HTTP helpers ready with degraded features: enabled=%s degraded=%s",
            STARTUP_TOTAL_STEPS,
            ", ".join(runtime_http_enabled) if runtime_http_enabled else "none",
            "; ".join(runtime_http_degraded),
        )
    else:
        _log_lifecycle_step("Startup", 2, STARTUP_TOTAL_STEPS, "Runtime HTTP helpers ready")

    _log_lifecycle_step("Startup", 3, STARTUP_TOTAL_STEPS, "Bootstrapping site runtime manager")
    try:
        from infrastructure.site_catalog.youtube_oauth import get_oauth_credentials_for_daemon
        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file
        bootstrap_site_runtimes()
        _log_lifecycle_step("Startup", 3, STARTUP_TOTAL_STEPS, "Site runtime manager ready")
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("Startup [3/%s] Failed to bootstrap site runtime manager", STARTUP_TOTAL_STEPS)
        raise

    _log_lifecycle_step("Startup", 4, STARTUP_TOTAL_STEPS, "Seeding video extraction projection")
    try:
        import domains.video.application.services.extraction_projection.service as video_extraction_projection_service
        rebuilt_count = video_extraction_projection_service.ensure_projection_seeded()
        _log_lifecycle_step(
            "Startup",
            4,
            STARTUP_TOTAL_STEPS,
            f"Video extraction projection ready (rebuilt={rebuilt_count})",
        )
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("Startup [4/%s] Failed to seed video extraction projection", STARTUP_TOTAL_STEPS)
        raise

    _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Bootstrapping scheduled tasks")
    try:
        from infrastructure.scheduling.bootstrap import ensure_system_tasks
        ensure_system_tasks()
        clear_optional_startup_issue("scheduled_task_bootstrap")
        _log_lifecycle_step("Startup", 5, STARTUP_TOTAL_STEPS, "Scheduled tasks ready")
    except Exception as exc:  # startup/shutdown boundary -- prevent crash during lifecycle
        record_optional_startup_issue("scheduled_task_bootstrap", exc)
        logger.warning(
            "Startup [5/%s] Scheduled task bootstrap degraded: %s",
            STARTUP_TOTAL_STEPS,
            exc,
            exc_info=True,
        )

    _log_lifecycle_step("Startup", 6, STARTUP_TOTAL_STEPS, "Ensuring Meilisearch index")
    if settings.SEARCH_BACKEND == 'meilisearch':
        # Meili 是 SEARCH_BACKEND=meilisearch 时的强依赖，索引未就绪会导致 domain 过滤报错
        # 和召回异常，故失败直接终止启动（用户需自行 fallback 到 SEARCH_BACKEND=legacy）。
        try:
            from infrastructure.search.meili import ensure_videos_index
            ensure_videos_index()
            _log_lifecycle_step("Startup", 6, STARTUP_TOTAL_STEPS, "Meilisearch index ready")
        except Exception:  # startup/shutdown boundary -- fail-fast on missing Meilisearch
            logger.exception("Startup [6/%s] Failed to ensure Meilisearch index", STARTUP_TOTAL_STEPS)
            raise
    else:
        _log_lifecycle_step("Startup", 6, STARTUP_TOTAL_STEPS, "Meilisearch skipped (SEARCH_BACKEND != meilisearch)")

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


