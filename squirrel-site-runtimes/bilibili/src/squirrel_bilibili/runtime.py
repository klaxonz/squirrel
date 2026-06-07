from __future__ import annotations

from typing import Any

from crawl import (
    ExtractionResult,
    SiteRuntimeCapability,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeSite,
    VideoMeta,
    build_runtime_proxy_config,
    create_site_runtime,
)
from crawl import (
    load_local_attr as _load_local_attr,
)

DEFAULT_SITE_METADATA = {
    'label': 'Bilibili',
    'aliases': ['bili'],
    'http': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://www.bilibili.com',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }
    },
    'rate_limit': {
        'enabled': True,
        'min_interval': 3.0,
        'max_interval': 5.0,
    },
    'proxy': {
        'connect_timeout': 30.0,
        'read_timeout': 120.0,
        'write_timeout': 30.0,
        'pool_timeout': 30.0,
        'keepalive_expiry': 30.0,
        'max_connections': 50,
        'max_keepalive_connections': 50,
        'chunk_size': 2 * 1024 * 1024,
        'max_retries': 5,
        'enable_http2': True,
        'follow_redirects': True,
    },
    'login': {
        'check_url': 'https://api.bilibili.com/x/web-interface/nav',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
        },
        'timeout': 15.0,
    },
    'metadata': {
        'requires_cookies': True,
        'requires_login': True,
        'offline_thumbnails_download': True,
        'offline_thumbnails_display': False,
        'nsfw': False,
    },
}

SITE_RUNTIME_MANIFEST = SiteRuntimeManifest(
    runtime_id='bilibili',
    version='0.1.0',
    display_name='Bilibili',
    description='Bilibili crawl integration',
    capabilities=[
        SiteRuntimeCapability(
            name='check_login_status',
            description='Check the current Bilibili login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        SiteRuntimeCapability(
            name='import_subscriptions',
            description='Import followed Bilibili creators for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a Bilibili creator or collection URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a Bilibili subscription.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        SiteRuntimeCapability(
            name='extract_video',
            description='Extract structured metadata for a Bilibili video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='fetch_subtitles',
            description='Fetch subtitles for a Bilibili video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for Bilibili streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        SiteRuntimeSite(
            site_name='bilibili',
            domains=['bilibili.com', 'b23.tv'],
            test_url='https://www.bilibili.com',
            metadata=DEFAULT_SITE_METADATA,
            features=[
                'check_login_status',
                'import_subscriptions',
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'fetch_subtitles',
                'resolve_proxy_config',
            ],
        )
    ],
    permissions=[
        SiteRuntimePermission(
            name='network:http',
            description='Access Bilibili APIs over HTTP.',
        ),
        SiteRuntimePermission(
            name='cookies:read:site/bilibili',
            description='Read Bilibili cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def _extract_video(payload: dict[str, Any]) -> dict[str, Any]:
    from .video_api import build_base_info, fetch_video_info

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


def _resolve_proxy_config(domain: str | None = None) -> dict[str, Any]:
    default_proxy_config = {
        'connect_timeout': 30.0,
        'read_timeout': 120.0,
        'max_retries': 5,
        'chunk_size': 2 * 1024 * 1024,
        'max_connections': 50,
        'keepalive_expiry': 30.0,
        'enable_http2': True,
    }
    return build_runtime_proxy_config(
        site_slug='bilibili',
        site_domain='bilibili.com',
        default_site_headers={
            'Referer': 'https://www.bilibili.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        },
        default_proxy_config=default_proxy_config,
        domain=domain,
    )



def get_site_runtime():
    return create_site_runtime(
        manifest=SITE_RUNTIME_MANIFEST,
        health_message='Bilibili runtime is configured',
        capability_handlers={
            'extract_video': _extract_video,
        },
        check_login=lambda: _load_local_attr('auth', 'check_bilibili_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'BilibiliUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'BilibiliSubscription')(url=url),
        subtitles_provider_factory=lambda: _load_local_attr('subtitles', 'BilibiliSubtitlesProvider')(),
        default_subtitle_lang='ai-zh',
        default_subtitle_format='srt',
        proxy_config_builder=_resolve_proxy_config,
    )
