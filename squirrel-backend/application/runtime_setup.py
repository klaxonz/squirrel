"""Atomic runtime-setup operations shared by the FastAPI lifespan and worker bootstrap.

These are thin, side-effect-only wrappers around the primitives each bootstrap path
needs. They intentionally do NOT wrap errors or log: the two callers (``main.py``
async lifespan, ``application/lifespan.py`` sync worker bootstrap) have different
failure policies (fail-fast vs degraded) and different logging styles, so error
handling stays at the call site.

Previously these steps were duplicated verbatim between the two bootstrap paths;
gathering the *operations* here keeps them in lockstep without forcing a shared
error-handling policy.
"""
from __future__ import annotations

import os

from infrastructure.config.site_config_manager import apply_site_config_overrides
from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from infrastructure.site_catalog.runtime_http import (
    set_cloudflare_bypass_client,
    set_cookie_domain_resolver,
    set_cookie_file_resolver,
)
from infrastructure.site_runtimes.manager import bootstrap_site_runtimes


def apply_site_config() -> None:
    """Apply site configuration overrides (headers/proxy/rate-limit per site)."""
    apply_site_config_overrides()


def configure_cloudflare_bypass() -> None:
    """Install the Cloudflare bypass client into the runtime HTTP module."""
    from infrastructure.site_catalog.cloudflare_bypass import get_default_client

    set_cloudflare_bypass_client(get_default_client())


def configure_cookie_resolvers() -> None:
    """Install the cookie file + domain resolvers used by the SDK crawl layer."""
    set_cookie_file_resolver(resolve_cookie_file_for_url)
    set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)


def prepare_youtube_oauth_env() -> None:
    """Resolve the YouTube OAuth state file (if configured) and export it to the env."""
    from infrastructure.site_catalog.youtube_oauth import get_oauth_credentials_for_daemon

    oauth_file = get_oauth_credentials_for_daemon()
    if oauth_file:
        os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file


def start_site_runtimes() -> None:
    """Bootstrap the site runtime manager (discovers/launches plugin runtimes)."""
    bootstrap_site_runtimes()
