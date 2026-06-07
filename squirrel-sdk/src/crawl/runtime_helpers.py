"""Convenience helpers for composing runtime V2 plugin packages."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .runtime_models import SiteRuntimeHealthStatus, SiteRuntimeManifest
from .site_runtime import RuntimeStartHook, RuntimeStopHook, create_declarative_site_runtime
from .site_runtime_helpers import (
    PayloadHandler,
    build_extract_video_handler,
    build_health_check,
    build_import_subscriptions_handler,
    build_login_status_handler,
    build_proxy_config_handler,
    build_resolve_subscription_handler,
    build_rewrite_proxy_playlist_handler,
    build_subtitles_handler,
    build_sync_subscription_handler,
)

ObjectFactory = Callable[[], Any]


def create_site_runtime(
    *,
    manifest: SiteRuntimeManifest,
    health_message: str | None = None,
    health_check: Callable[[], SiteRuntimeHealthStatus] | None = None,
    on_start: RuntimeStartHook | None = None,
    on_stop: RuntimeStopHook | None = None,
    capability_handlers: dict[str, PayloadHandler] | None = None,
    check_login: Callable[[], Any] | None = None,
    importer_factory: ObjectFactory | None = None,
    subscription_factory: Callable[[str], Any] | None = None,
    extractor_factory: ObjectFactory | None = None,
    extractor_site_name: str | None = None,
    subtitles_provider_factory: ObjectFactory | None = None,
    default_subtitle_lang: str = 'en',
    default_subtitle_format: str = 'srt',
    proxy_config_builder: Callable[[Any], dict[str, Any]] | None = None,
    playlist_rewriter: Callable[[str, str | bytes, str | None], dict[str, Any]] | None = None,
):
    resolved_handlers = dict(capability_handlers or {})

    if check_login is not None:
        resolved_handlers.setdefault('check_login_status', build_login_status_handler(check_login))
    if importer_factory is not None:
        resolved_handlers.setdefault('import_subscriptions', build_import_subscriptions_handler(importer_factory))
    if subscription_factory is not None:
        resolved_handlers.setdefault('resolve_subscription', build_resolve_subscription_handler(subscription_factory))
        resolved_handlers.setdefault('sync_subscription', build_sync_subscription_handler(subscription_factory))
    if extractor_factory is not None and extractor_site_name:
        resolved_handlers.setdefault(
            'extract_video',
            build_extract_video_handler(extractor_site_name, extractor_factory),
        )
    if subtitles_provider_factory is not None:
        resolved_handlers.setdefault(
            'fetch_subtitles',
            build_subtitles_handler(
                subtitles_provider_factory,
                default_lang=default_subtitle_lang,
                default_fmt=default_subtitle_format,
            ),
        )
    if proxy_config_builder is not None:
        resolved_handlers.setdefault('resolve_proxy_config', build_proxy_config_handler(proxy_config_builder))
    if playlist_rewriter is not None:
        resolved_handlers.setdefault(
            'rewrite_proxy_playlist',
            build_rewrite_proxy_playlist_handler(playlist_rewriter),
        )

    effective_health_check = health_check
    if effective_health_check is None and health_message:
        effective_health_check = build_health_check(health_message)

    return create_declarative_site_runtime(
        manifest=manifest,
        capability_handlers=resolved_handlers,
        on_start=on_start,
        on_stop=on_stop,
        health_check=effective_health_check,
    )
