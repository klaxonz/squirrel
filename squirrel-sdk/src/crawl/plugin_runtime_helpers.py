"""Helpers for composing plugin runtime V2 capability handlers."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Dict, Optional

from .core import ExtractionTask, SubscriptionSyncContext
from .plugin import create_plugin_runtime
from .runtime_models import PluginHealthStatus, PluginManifest


Payload = Dict[str, Any]
ObjectFactory = Callable[[], Any]
PayloadHandler = Callable[[Payload], Dict[str, Any]]


def require_payload_str(payload: Payload, field: str, *, label: Optional[str] = None) -> str:
    value = str(payload.get(field) or '').strip()
    if not value:
        raise ValueError(f'Missing {label or field}')
    return value


def build_subscription_sync_context(payload: Payload) -> SubscriptionSyncContext:
    return SubscriptionSyncContext(
        mode=str(payload.get('mode') or 'incremental'),
        cursor_payload=dict(payload.get('cursor_payload') or {}),
        last_seen_video_url=payload.get('last_seen_video_url'),
        limit=payload.get('limit'),
    )


def build_video_ref(payload: Payload, *, include_duration: bool = False) -> SimpleNamespace:
    data = {
        'id': payload.get('video_id'),
        'url': require_payload_str(payload, 'url', label='video url'),
        'title': payload.get('title'),
    }
    if include_duration:
        data['duration'] = payload.get('duration')
    return SimpleNamespace(**data)


def build_health_check(message: str, *, status: str = 'ready') -> Callable[[], PluginHealthStatus]:
    def _health_check() -> PluginHealthStatus:
        return PluginHealthStatus(
            healthy=True,
            status=status,
            message=message,
        )

    return _health_check


def build_plugin_runtime(
    manifest: PluginManifest,
    capability_handlers: Dict[str, PayloadHandler],
    *,
    health_message: Optional[str] = None,
    health_check: Optional[Callable[[], PluginHealthStatus]] = None,
):
    effective_health_check = health_check
    if effective_health_check is None and health_message:
        effective_health_check = build_health_check(health_message)

    return create_plugin_runtime(
        manifest=manifest,
        capability_handlers=capability_handlers,
        health_check=effective_health_check,
    )


def build_login_status_handler(checker: Callable[[], Any]) -> PayloadHandler:
    def _handler(_payload: Payload) -> Dict[str, Any]:
        return checker().to_dict()

    return _handler


def build_import_subscriptions_handler(importer_factory: ObjectFactory) -> PayloadHandler:
    def _handler(_payload: Payload) -> Dict[str, Any]:
        importer = importer_factory()
        items = importer.get_user_subscriptions()
        return {
            'items': [item.to_dict() for item in items],
            'total': len(items),
        }

    return _handler


def build_resolve_subscription_handler(subscription_factory: Callable[[str], Any]) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        url = require_payload_str(payload, 'url', label='subscription url')
        return subscription_factory(url).get_subscribe_info().to_dict()

    return _handler


def build_sync_subscription_handler(subscription_factory: Callable[[str], Any]) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        url = require_payload_str(payload, 'url', label='subscription url')
        subscription = subscription_factory(url)
        context = build_subscription_sync_context(payload)
        return subscription.sync_videos(context).to_dict()

    return _handler


def build_extract_video_handler(site_name: str, extractor_factory: ObjectFactory) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        url = require_payload_str(payload, 'url', label='video url')
        extractor = extractor_factory()
        return extractor.extract(ExtractionTask(url=url, site_name=site_name)).to_dict()

    return _handler


def build_resolve_playback_handler(handler_factory: ObjectFactory) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        handler = handler_factory()
        return handler.get_video_url(build_video_ref(payload))

    return _handler


def build_subtitles_handler(
    provider_factory: ObjectFactory,
    *,
    default_lang: str,
    default_fmt: str = 'srt',
) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        provider = provider_factory()
        lang = str(payload.get('lang') or default_lang).strip() or default_lang
        fmt = str(payload.get('fmt') or default_fmt).strip() or default_fmt
        content, filename = provider.get_subtitles(build_video_ref(payload), lang, fmt)
        return {
            'content': content,
            'filename': filename,
            'media_type': 'text/plain; charset=utf-8',
        }

    return _handler


def build_mpd_handler(builder_factory: ObjectFactory, *, include_duration: bool = False) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        builder = builder_factory()
        content = builder.build_mpd(build_video_ref(payload, include_duration=include_duration))
        return {
            'content': content,
            'media_type': 'application/dash+xml',
        }

    return _handler


def build_proxy_config_handler(builder: Callable[[Any], Dict[str, Any]]) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        return builder(payload.get('domain'))

    return _handler


def build_rewrite_proxy_playlist_handler(rewriter: Callable[[str, str | bytes, Optional[str]], Dict[str, Any]]) -> PayloadHandler:
    def _handler(payload: Payload) -> Dict[str, Any]:
        url = require_payload_str(payload, 'url', label='playlist url')
        return rewriter(
            url,
            payload.get('content') or '',
            referer=payload.get('referer'),
        )

    return _handler
