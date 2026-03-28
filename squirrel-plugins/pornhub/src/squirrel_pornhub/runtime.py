from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from crawl import (
    ExtractionTask,
    PluginCapability,
    PluginHealthStatus,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
    SubscriptionSyncContext,
    create_plugin_runtime,
)

PLUGIN_MANIFEST = PluginManifest(
    plugin_id='pornhub',
    version='0.1.0',
    display_name='Pornhub',
    description='Pornhub crawl integration',
    capabilities=[
        PluginCapability(
            name='check_login_status',
            description='Check the current Pornhub login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='import_subscriptions',
            description='Import followed Pornhub creators for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a Pornhub creator URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a Pornhub subscription.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='extract_video',
            description='Extract structured metadata for a Pornhub video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_playback',
            description='Resolve playback URLs for a Pornhub video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
    ],
    sites=[
        PluginSiteManifest(
            site_name='pornhub',
            domains=['pornhub.com'],
            test_url='https://www.pornhub.com',
            features=[
                'check_login_status',
                'import_subscriptions',
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'resolve_playback',
            ],
        )
    ],
    permissions=[
        PluginPermission(
            name='network:http',
            description='Access Pornhub APIs and web pages over HTTP.',
        ),
        PluginPermission(
            name='cookies:read:site/pornhub',
            description='Read Pornhub cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def _check_login_status(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .auth import check_pornhub_login_status

    result = check_pornhub_login_status()
    return result.to_dict()


def _import_subscriptions(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .importer import PornhubUserSubscriptionImporter

    importer = PornhubUserSubscriptionImporter()
    items = importer.get_user_subscriptions()
    return {
        'items': [item.to_dict() for item in items],
        'total': len(items),
    }


def _resolve_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import PornhubSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = PornhubSubscription(url=url)
    return subscription.get_subscribe_info().to_dict()


def _sync_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import PornhubSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = PornhubSubscription(url=url)
    context = SubscriptionSyncContext(
        mode=str(payload.get('mode') or 'incremental'),
        cursor_payload=dict(payload.get('cursor_payload') or {}),
        last_seen_video_url=payload.get('last_seen_video_url'),
        limit=payload.get('limit'),
    )
    return subscription.sync_videos(context).to_dict()


def _extract_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .extractor import PornhubExtractor

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing video url')

    extractor = PornhubExtractor()
    result = extractor.extract(ExtractionTask(url=url, site_name='pornhub'))
    return result.to_dict()


def _resolve_playback(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .handler import PornhubHandler

    url = str(payload.get('url') or '').strip()
    video_id = payload.get('video_id')
    if not url:
        raise ValueError('Missing playback url')

    handler = PornhubHandler()
    return handler.get_video_url(
        SimpleNamespace(
            id=video_id,
            url=url,
            title=payload.get('title'),
        )
    )


def _health_check() -> PluginHealthStatus:
    return PluginHealthStatus(
        healthy=True,
        status='ready',
        message='Pornhub runtime is configured',
    )


def get_plugin_runtime():
    return create_plugin_runtime(
        manifest=PLUGIN_MANIFEST,
        capability_handlers={
            'check_login_status': _check_login_status,
            'import_subscriptions': _import_subscriptions,
            'resolve_subscription': _resolve_subscription,
            'sync_subscription': _sync_subscription,
            'extract_video': _extract_video,
            'resolve_playback': _resolve_playback,
        },
        health_check=_health_check,
    )
