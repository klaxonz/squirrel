"""Shared runtime setup steps used by both the FastAPI lifespan and the worker bootstrap.

These three pieces were previously duplicated between ``main.py:lifespan`` (async, FastAPI)
and ``application/lifespan.py:bootstrap_runtime`` (sync, workers). They are gathered here so
the two bootstrap paths stay in lockstep without copy-pasted try/except scaffolding.

Each helper is tolerant of being called from either context: callers wrap them as needed.
"""
from __future__ import annotations

import logging
import os

from infrastructure.config.site_config_manager import apply_site_config_overrides
from infrastructure.config.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
)
from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from infrastructure.site_catalog.runtime_http import (
    set_cloudflare_bypass_client,
    set_cookie_domain_resolver,
    set_cookie_file_resolver,
)
from infrastructure.site_runtimes.manager import bootstrap_site_runtimes

logger = logging.getLogger(__name__)


def apply_site_config(component: str = "Startup") -> None:
    """Apply site configuration overrides. Raises on failure (hard dependency)."""
    try:
        apply_site_config_overrides()
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Failed to apply site configuration overrides", component)
        raise


def configure_runtime_http(component: str = "Startup") -> None:
    """Configure the Cloudflare bypass client and cookie resolvers.

    Cloudflare bypass is an optional capability: failure is recorded as a degraded startup
    issue rather than fatal. Cookie resolvers are a hard dependency.
    """
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client

        set_cloudflare_bypass_client(get_default_client())
        clear_optional_startup_issue("cloudflare_bypass")
    except Exception as exc:  # startup/shutdown boundary -- optional capability
        record_optional_startup_issue("cloudflare_bypass", exc)
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)

    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Failed to configure cookie resolver", component)
        raise


def bootstrap_site_runtimes_with_oauth(component: str = "Startup") -> None:
    """Resolve YouTube OAuth state file (if any) and bootstrap the site runtime manager.

    Raises on failure (site runtimes are required for plugin-driven capabilities).
    """
    try:
        from infrastructure.site_catalog.youtube_oauth import get_oauth_credentials_for_daemon

        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file
        bootstrap_site_runtimes()
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Failed to bootstrap site runtime manager", component)
        raise
