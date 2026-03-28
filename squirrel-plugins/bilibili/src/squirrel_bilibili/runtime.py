from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from crawl import (
    ExtractionResult,
    get_http_headers,
    get_proxy_config,
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
            name='resolve_subscription',
            description='Resolve subscription metadata for a Bilibili creator or collection URL.',
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
        PluginCapability(
            name='fetch_subtitles',
            description='Fetch subtitles for a Bilibili video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='build_mpd',
            description='Build an MPD document for a Bilibili video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for Bilibili streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
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
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'resolve_playback',
                'fetch_subtitles',
                'build_mpd',
                'resolve_proxy_config',
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


def _resolve_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import BilibiliSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = BilibiliSubscription(url=url)
    return subscription.get_subscribe_info().to_dict()


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
    return handler.get_video_url(SimpleNamespace(id=video_id, url=url, title=payload.get('title')))


def _fetch_subtitles(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subtitles import BilibiliSubtitlesProvider

    url = str(payload.get('url') or '').strip()
    lang = str(payload.get('lang') or 'ai-zh').strip() or 'ai-zh'
    fmt = str(payload.get('fmt') or 'srt').strip() or 'srt'
    if not url:
        raise ValueError('Missing video url')

    provider = BilibiliSubtitlesProvider()
    content, filename = provider.get_subtitles(
        SimpleNamespace(id=payload.get('video_id'), url=url),
        lang,
        fmt,
    )
    return {
        'content': content,
        'filename': filename,
        'media_type': 'text/plain; charset=utf-8',
    }


def _build_mpd(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .mpd import BilibiliMpdBuilder

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing video url')

    builder = BilibiliMpdBuilder()
    content = builder.build_mpd(SimpleNamespace(id=payload.get('video_id'), url=url))
    return {
        'content': content,
        'media_type': 'application/dash+xml',
    }


def _resolve_proxy_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = {
        'connect_timeout': 30.0,
        'read_timeout': 120.0,
        'max_retries': 5,
        'chunk_size': 2 * 1024 * 1024,
        'max_connections': 50,
        'keepalive_expiry': 30.0,
        'enable_http2': True,
    }
    config.update(get_proxy_config('bilibili'))

    return {
        'site_headers': get_http_headers('bilibili', {
            'Referer': 'https://www.bilibili.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        }),
        'domain_configs': [{
            'domain': str(payload.get('domain') or 'bilibili.com').strip().lower() or 'bilibili.com',
            'connect_timeout': float(config['connect_timeout']),
            'read_timeout': float(config['read_timeout']),
            'max_retries': int(config['max_retries']),
            'chunk_size': int(config['chunk_size']),
            'max_connections': int(config['max_connections']),
            'keepalive_expiry': float(config['keepalive_expiry']),
            'enable_http2': bool(config['enable_http2']),
        }],
    }


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
            'resolve_subscription': _resolve_subscription,
            'sync_subscription': _sync_subscription,
            'extract_video': _extract_video,
            'resolve_playback': _resolve_playback,
            'fetch_subtitles': _fetch_subtitles,
            'build_mpd': _build_mpd,
            'resolve_proxy_config': _resolve_proxy_config,
        },
        health_check=_health_check,
    )
