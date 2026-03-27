from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from crawl import (
    ExtractionResult,
    PluginCapability,
    PluginHealthStatus,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
    SubscriptionSyncContext,
    VideoMeta,
    create_plugin_runtime,
)

PLUGIN_MANIFEST = PluginManifest(
    plugin_id='bilibili',
    version='0.1.0',
    display_name='Bilibili',
    description='Bilibili crawl integration',
    capabilities=[
        PluginCapability(
            name='check_login_status',
            description='Check the current Bilibili login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='import_subscriptions',
            description='Import followed Bilibili creators for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a Bilibili subscription.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='extract_video',
            description='Extract structured metadata for a Bilibili video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_playback',
            description='Resolve playback URLs for a Bilibili video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
    ],
    sites=[
        PluginSiteManifest(
            site_name='bilibili',
            domains=['bilibili.com', 'b23.tv'],
            test_url='https://www.bilibili.com',
            features=[
                'check_login_status',
                'import_subscriptions',
                'sync_subscription',
                'extract_video',
                'resolve_playback',
            ],
        )
    ],
    permissions=[
        PluginPermission(
            name='network:http',
            description='Access Bilibili APIs over HTTP.',
        ),
        PluginPermission(
            name='cookies:read:site/bilibili',
            description='Read Bilibili cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def _check_login_status(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .auth import check_bilibili_login_status

    result = check_bilibili_login_status()
    return result.to_dict()


def _import_subscriptions(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .importer import BilibiliUserSubscriptionImporter

    importer = BilibiliUserSubscriptionImporter()
    items = importer.get_user_subscriptions()
    return {
        'items': [item.to_dict() for item in items],
        'total': len(items),
    }


def _sync_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import BilibiliSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = BilibiliSubscription(url=url)
    context = SubscriptionSyncContext(
        mode=str(payload.get('mode') or 'incremental'),
        cursor_payload=dict(payload.get('cursor_payload') or {}),
        last_seen_video_url=payload.get('last_seen_video_url'),
        limit=payload.get('limit'),
    )
    return subscription.sync_videos(context).to_dict()


def _extract_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .sign import build_base_info, fetch_video_info

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing video url')

    info, context, page_info = fetch_video_info(url)
    base_info = build_base_info(info, context, page_info)
    video_meta = VideoMeta(
        title=base_info.get('title') or '',
        url=url,
        thumbnail=base_info.get('thumbnail'),
        duration=base_info.get('duration'),
        publish_date=base_info.get('publish_date'),
        extra_data={
            'id': base_info.get('id'),
            'bvid': base_info.get('bvid'),
            'aid': base_info.get('aid'),
            'cid': base_info.get('cid'),
            'description': base_info.get('description'),
            'owner': base_info.get('owner'),
            'pages': base_info.get('pages'),
            'dynamic': base_info.get('dynamic'),
            'upload_date': base_info.get('upload_date'),
        },
    )
    return ExtractionResult.success_result(video_meta).to_dict()


def _resolve_playback(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .handler import BilibiliHandler

    url = str(payload.get('url') or '').strip()
    video_id = payload.get('video_id')
    if not url:
        raise ValueError('Missing playback url')

    handler = BilibiliHandler()
    return handler.get_video_url(SimpleNamespace(id=video_id, url=url))


def _health_check() -> PluginHealthStatus:
    return PluginHealthStatus(
        healthy=True,
        status='ready',
        message='Bilibili runtime is configured',
    )


def get_plugin_runtime():
    return create_plugin_runtime(
        manifest=PLUGIN_MANIFEST,
        capability_handlers={
            'check_login_status': _check_login_status,
            'import_subscriptions': _import_subscriptions,
            'sync_subscription': _sync_subscription,
            'extract_video': _extract_video,
            'resolve_playback': _resolve_playback,
        },
        health_check=_health_check,
    )
