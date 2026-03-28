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
    plugin_id='youtube',
    version='0.1.0',
    display_name='YouTube',
    description='YouTube crawl integration',
    capabilities=[
        PluginCapability(
            name='check_login_status',
            description='Check the current YouTube login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='import_subscriptions',
            description='Import followed YouTube channels for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a YouTube channel or playlist URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a YouTube subscription.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='extract_video',
            description='Extract structured metadata for a YouTube video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_playback',
            description='Resolve playback URLs for a YouTube video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='fetch_subtitles',
            description='Fetch subtitles for a YouTube video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='build_mpd',
            description='Build an MPD document for a YouTube video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for YouTube streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied YouTube playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        PluginSiteManifest(
            site_name='youtube',
            domains=['youtube.com', 'youtu.be'],
            test_url='https://www.youtube.com',
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
                'rewrite_proxy_playlist',
            ],
        )
    ],
    permissions=[
        PluginPermission(
            name='network:http',
            description='Access YouTube APIs and web pages over HTTP.',
        ),
        PluginPermission(
            name='cookies:read:site/youtube',
            description='Read YouTube cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def _check_login_status(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .auth import check_youtube_login_status

    result = check_youtube_login_status()
    return result.to_dict()


def _import_subscriptions(_payload: Dict[str, Any]) -> Dict[str, Any]:
    from .importer import YoutubeUserSubscriptionImporter

    importer = YoutubeUserSubscriptionImporter()
    items = importer.get_user_subscriptions()
    return {
        'items': [item.to_dict() for item in items],
        'total': len(items),
    }


def _resolve_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import YoutubeSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = YoutubeSubscription(url=url)
    return subscription.get_subscribe_info().to_dict()


def _sync_subscription(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subscription import YoutubeSubscription

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing subscription url')

    subscription = YoutubeSubscription(url=url)
    context = SubscriptionSyncContext(
        mode=str(payload.get('mode') or 'incremental'),
        cursor_payload=dict(payload.get('cursor_payload') or {}),
        last_seen_video_url=payload.get('last_seen_video_url'),
        limit=payload.get('limit'),
    )
    return subscription.sync_videos(context).to_dict()


def _extract_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .extractor import YoutubeExtractor

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing video url')

    extractor = YoutubeExtractor()
    result = extractor.extract(ExtractionTask(url=url, site_name='youtube'))
    return result.to_dict()


def _resolve_playback(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .handler import YouTubeHandler

    url = str(payload.get('url') or '').strip()
    video_id = payload.get('video_id')
    if not url:
        raise ValueError('Missing playback url')

    handler = YouTubeHandler()
    return handler.get_video_url(
        SimpleNamespace(
            id=video_id,
            url=url,
            title=payload.get('title'),
        )
    )


def _fetch_subtitles(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .subtitles import YoutubeSubtitlesProvider

    url = str(payload.get('url') or '').strip()
    lang = str(payload.get('lang') or 'en').strip() or 'en'
    fmt = str(payload.get('fmt') or 'srt').strip() or 'srt'
    if not url:
        raise ValueError('Missing video url')

    provider = YoutubeSubtitlesProvider()
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
    from .mpd import YouTubeMpdBuilder

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing video url')

    builder = YouTubeMpdBuilder()
    content = builder.build_mpd(SimpleNamespace(id=payload.get('video_id'), url=url, duration=payload.get('duration')))
    return {
        'content': content,
        'media_type': 'application/dash+xml',
    }


def _resolve_proxy_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .proxy import build_runtime_proxy_config

    return build_runtime_proxy_config(payload.get('domain'))


def _rewrite_proxy_playlist(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .proxy import rewrite_proxy_playlist

    url = str(payload.get('url') or '').strip()
    if not url:
        raise ValueError('Missing playlist url')
    return rewrite_proxy_playlist(
        url,
        payload.get('content') or '',
        referer=payload.get('referer'),
    )


def _health_check() -> PluginHealthStatus:
    return PluginHealthStatus(
        healthy=True,
        status='ready',
        message='YouTube runtime is configured',
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
            'rewrite_proxy_playlist': _rewrite_proxy_playlist,
        },
        health_check=_health_check,
    )
