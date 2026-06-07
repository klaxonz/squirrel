"""Helpers for composing site runtime capability handlers."""
from __future__ import annotations

import inspect
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

from .core import (
    ExtractionTask,
    PaginatedUserSubscriptionImporter,
    SubscriptionImportBatchResult,
    SubscriptionSyncContext,
    UserSubscriptionImporter,
)
from .exceptions import NoSubtitlesError
from .runtime_errors import SiteRuntimeError
from .runtime_models import SiteRuntimeHealthStatus, SiteRuntimeInvokeResponse, SiteRuntimeManifest
from .site_runtime import create_declarative_site_runtime

Payload = dict[str, Any]
ObjectFactory = Callable[[], Any]
PayloadHandler = Callable[[Payload], dict[str, Any] | SiteRuntimeInvokeResponse]


def require_payload_str(payload: Payload, field: str, *, label: str | None = None) -> str:
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
    if 'client_type' in payload:
        data['client_type'] = payload.get('client_type')
    if 'direct_playback' in payload:
        data['direct_playback'] = bool(payload.get('direct_playback'))
    return SimpleNamespace(**data)


def build_health_check(message: str, *, status: str = 'ready') -> Callable[[], SiteRuntimeHealthStatus]:
    def _health_check() -> SiteRuntimeHealthStatus:
        return SiteRuntimeHealthStatus(
            healthy=True,
            status=status,
            message=message,
        )

    return _health_check


def build_site_runtime(
    manifest: SiteRuntimeManifest,
    capability_handlers: dict[str, PayloadHandler],
    *,
    health_message: str | None = None,
    health_check: Callable[[], SiteRuntimeHealthStatus] | None = None,
):
    effective_health_check = health_check
    if effective_health_check is None and health_message:
        effective_health_check = build_health_check(health_message)

    return create_declarative_site_runtime(
        manifest=manifest,
        capability_handlers=capability_handlers,
        health_check=effective_health_check,
    )


def build_login_status_handler(checker: Callable[[], Any]) -> PayloadHandler:
    def _handler(_payload: Payload) -> dict[str, Any]:
        return checker().to_dict()

    return _handler


def build_import_subscriptions_handler(importer_factory: ObjectFactory) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        importer = importer_factory()
        cursor_payload = dict(payload.get('cursor_payload') or {})
        limit = payload.get('limit')

        if hasattr(importer, 'get_user_subscriptions_batch'):
            batch_result = cast(
                PaginatedUserSubscriptionImporter,
                importer,
            ).get_user_subscriptions_batch(
                cursor_payload=cursor_payload or None,
                limit=limit,
            )
        else:
            all_items = cast(UserSubscriptionImporter, importer).get_user_subscriptions()
            batch_result = _build_import_batch_from_items(
                all_items,
                cursor_payload=cursor_payload or None,
                limit=limit,
            )

        items = batch_result.items
        return {
            'items': [item.to_dict() for item in items],
            'total': len(items),
            'cursor_payload': batch_result.cursor_payload,
            'has_more': batch_result.has_more,
            'stop_reason': batch_result.stop_reason,
            'total_available': batch_result.total_available,
        }

    return _handler


def _build_import_batch_from_items(
    items: list[Any],
    *,
    cursor_payload: dict[str, Any] | None = None,
    limit: Any = None,
) -> SubscriptionImportBatchResult:
    offset = 0
    if cursor_payload:
        try:
            offset = max(int(cursor_payload.get('offset', 0) or 0), 0)
        except (TypeError, ValueError):
            offset = 0

    normalized_limit: int | None
    try:
        normalized_limit = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        normalized_limit = None
    if normalized_limit is not None and normalized_limit <= 0:
        normalized_limit = None

    if normalized_limit is None:
        batch_items = list(items[offset:])
    else:
        batch_items = list(items[offset:offset + normalized_limit])

    next_offset = offset + len(batch_items)
    has_more = next_offset < len(items)

    return SubscriptionImportBatchResult(
        items=[
            item if hasattr(item, 'to_dict') else item
            for item in batch_items
        ],
        cursor_payload={'offset': next_offset} if has_more else None,
        has_more=has_more,
        stop_reason='batch_exhausted' if has_more else 'source_exhausted',
        total_available=len(items),
    )


def build_resolve_subscription_handler(subscription_factory: Callable[[str], Any]) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        url = require_payload_str(payload, 'url', label='subscription url')
        return subscription_factory(url).get_subscribe_info().to_dict()

    return _handler


def build_sync_subscription_handler(subscription_factory: Callable[[str], Any]) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        url = require_payload_str(payload, 'url', label='subscription url')
        subscription = subscription_factory(url)
        context = build_subscription_sync_context(payload)
        return subscription.sync_videos(context).to_dict()

    return _handler


def build_extract_video_handler(site_name: str, extractor_factory: ObjectFactory) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        url = require_payload_str(payload, 'url', label='video url')
        extractor = extractor_factory()
        return extractor.extract(ExtractionTask(url=url, site_name=site_name)).to_dict()

    return _handler


def build_subtitles_handler(
    provider_factory: ObjectFactory,
    *,
    default_lang: str,
    default_fmt: str = 'srt',
) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        provider = provider_factory()
        lang = str(payload.get('lang') or default_lang).strip() or default_lang
        fmt = str(payload.get('fmt') or default_fmt).strip() or default_fmt
        try:
            content, filename = provider.get_subtitles(build_video_ref(payload), lang, fmt)
        except NoSubtitlesError as exc:
            return SiteRuntimeInvokeResponse(
                request_id=str(payload.get('request_id') or ''),
                ok=False,
                error=SiteRuntimeError.subtitles_not_available(
                    'No subtitles available',
                    details={'reason': str(exc)},
                ),
            )
        return {
            'content': content,
            'filename': filename,
            'media_type': 'text/vtt; charset=utf-8' if fmt.lower() == 'vtt' else 'text/plain; charset=utf-8',
        }

    return _handler


def build_proxy_config_handler(builder: Callable[[Any], dict[str, Any]]) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        signature = inspect.signature(builder)
        params = list(signature.parameters.values())
        if not params:
            return builder()

        first = params[0]
        if first.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            return builder(dict(payload or {}))

        first_name = first.name.strip().lower()
        if first_name in {'payload', 'request', 'context', 'proxy_payload', 'proxy_request'}:
            return builder(dict(payload or {}))

        return builder(payload.get('domain'))

    return _handler


def build_rewrite_proxy_playlist_handler(rewriter: Callable[[str, str | bytes, str | None], dict[str, Any]]) -> PayloadHandler:
    def _handler(payload: Payload) -> dict[str, Any]:
        url = require_payload_str(payload, 'url', label='playlist url')
        return rewriter(
            url,
            payload.get('content') or '',
            referer=payload.get('referer'),
        )

    return _handler
