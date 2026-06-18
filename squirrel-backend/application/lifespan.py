"""FastAPI application lifespan: web-process startup/shutdown orchestration.

This is the async lifespan bound to the FastAPI app in ``main.py``. It is the
web-process counterpart to ``workers/bootstrap.py`` (sync, for worker processes):
both initialize the same shared runtime (logging, db, site config, http,
site plugins), but the web process runs inside FastAPI's lifespan protocol.
"""
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from application.startup_health import StartupHealth
from infrastructure.config.settings import settings
from infrastructure.runtime.site_config_manager import apply_site_config_overrides
from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from infrastructure.site_catalog.runtime_http import (
    set_cloudflare_bypass_client,
    set_cookie_domain_resolver,
    set_cookie_file_resolver,
)
from infrastructure.site_plugins.registry import get_site_plugin_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI application lifecycle: bootstrap runtime, serve, then shut down."""
    logger.info("Startup: begin")
    startup_issues = StartupHealth()
    app.state.startup_health = startup_issues

    for notice in settings.optional_feature_warnings():
        logger.warning("Startup: %s", notice)

    # 1. Site config (hard dependency)
    logger.info("Startup: applying site configuration overrides")
    try:
        apply_site_config_overrides()
    except Exception:
        logger.exception("Startup: failed to apply site configuration overrides")
        raise

    # 2. Runtime HTTP: cloudflare bypass is optional (degrade), cookie resolver is required
    logger.info("Startup: configuring runtime HTTP helpers")
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client

        set_cloudflare_bypass_client(get_default_client())
        startup_issues.clear("cloudflare_bypass")
    except Exception as exc:
        startup_issues.record_optional("cloudflare_bypass", exc)
        logger.warning("Startup: cloudflare bypass disabled: %s", exc)
    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
    except Exception:
        logger.exception("Startup: failed to configure cookie resolver")
        raise

    # 3. Site plugins (hard dependency) — YouTube OAuth env must be set before plugin start
    logger.info("Startup: starting site plugins")
    try:
        from infrastructure.site_catalog.youtube_oauth import get_oauth_credentials_for_daemon

        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file
        get_site_plugin_registry().start_all()
    except Exception:
        logger.exception("Startup: failed to start site plugins")
        raise

    # 4. Scheduled tasks (degraded-tolerant)
    logger.info("Startup: bootstrapping scheduled tasks")
    try:
        from infrastructure.scheduling.bootstrap import ensure_system_tasks

        ensure_system_tasks()
        startup_issues.clear("scheduled_task_bootstrap")
    except Exception as exc:
        startup_issues.record_optional("scheduled_task_bootstrap", exc)
        logger.warning("Startup: scheduled task bootstrap degraded: %s", exc, exc_info=True)

    # 5. Meilisearch index (hard dependency when configured; skipped if MEILISEARCH_URL unset)
    logger.info("Startup: ensuring Meilisearch index")
    if settings.meili.url:
        try:
            from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
            from infrastructure.search.meili import ensure_videos_index

            ensure_videos_index()
            get_meili_video_indexer()  # 预热单例，避免首个请求的初始化开销
        except Exception:
            logger.exception("Startup: failed to ensure Meilisearch index")
            raise
    else:
        logger.warning("Startup: MEILISEARCH_URL not configured -- search disabled")

    logger.info("Startup: complete")

    yield

    logger.info("Shutdown: begin")
    try:
        get_site_plugin_registry().stop_all()
    except Exception as exc:  # cleanup during shutdown -- must not propagate
        logger.warning("Shutdown: error stopping site plugins (ignored): %s", exc)
    logger.info("Shutdown: complete")
