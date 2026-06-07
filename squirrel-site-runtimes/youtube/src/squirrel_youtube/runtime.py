from __future__ import annotations

from crawl import (
    SiteRuntimeCapability,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeSite,
    create_site_runtime,
)
from crawl import (
    load_local_attr as _load_local_attr,
)

from .youtubei_resolver import prewarm_youtubei_worker, shutdown_youtubei_worker

DEFAULT_SITE_METADATA = {
    'label': 'YouTube',
    'aliases': ['yt'],
    'http': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    },
    'rate_limit': {
        'enabled': True,
        'min_interval': 2.0,
        'max_interval': 5.0,
    },
    'proxy': {
        'connect_timeout': 30.0,
        'read_timeout': 180.0,
        'write_timeout': 30.0,
        'pool_timeout': 30.0,
        'keepalive_expiry': 60.0,
        'max_connections': 100,
        'max_keepalive_connections': 50,
        'chunk_size': 2 * 1024 * 1024,
        'max_retries': 5,
        'enable_http2': True,
        'follow_redirects': True,
    },
    'login': {
        'check_url': 'https://www.youtube.com/feed/channels',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'timeout': 20.0,
    },
    'cookie': {
        'alias_domains': ['googlevideo.com', 'gvt1.com', 'ytimg.com'],
        'match_domain': 'youtube.com',
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
    runtime_id='youtube',
    version='0.1.0',
    display_name='YouTube',
    description='YouTube crawl integration',
    capabilities=[
        SiteRuntimeCapability(
            name='check_login_status',
            description='Check the current YouTube login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        SiteRuntimeCapability(
            name='import_subscriptions',
            description='Import followed YouTube channels for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a YouTube channel or playlist URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a YouTube subscription.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        SiteRuntimeCapability(
            name='extract_video',
            description='Extract structured metadata for a YouTube video URL.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        SiteRuntimeCapability(
            name='fetch_subtitles',
            description='Fetch subtitles for a YouTube video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for YouTube streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        SiteRuntimeCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied YouTube playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        SiteRuntimeSite(
            site_name='youtube',
            domains=['youtube.com', 'youtu.be'],
            test_url='https://www.youtube.com',
            metadata=DEFAULT_SITE_METADATA,
            features=[
                'check_login_status',
                'import_subscriptions',
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'fetch_subtitles',
                'resolve_proxy_config',
                'rewrite_proxy_playlist',
            ],
        )
    ],
    permissions=[
        SiteRuntimePermission(
            name='network:http',
            description='Access YouTube APIs and web pages over HTTP.',
        ),
        SiteRuntimePermission(
            name='cookies:read:site/youtube',
            description='Read YouTube cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def get_site_runtime():
    return create_site_runtime(
        manifest=SITE_RUNTIME_MANIFEST,
        health_message='YouTube runtime is configured',
        on_start=lambda _context: prewarm_youtubei_worker(),
        on_stop=shutdown_youtubei_worker,
        check_login=lambda: _load_local_attr('auth', 'check_youtube_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'YoutubeUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'YoutubeSubscription')(url=url),
        extractor_factory=lambda: _load_local_attr('extractor', 'YoutubeExtractor')(),
        extractor_site_name='youtube',
        subtitles_provider_factory=lambda: _load_local_attr('subtitles', 'YoutubeSubtitlesProvider')(),
        default_subtitle_lang='en',
        default_subtitle_format='srt',
        proxy_config_builder=lambda domain: _load_local_attr('proxy', 'build_runtime_proxy_config')(domain),
        playlist_rewriter=lambda url, content, referer=None: _load_local_attr('proxy', 'rewrite_proxy_playlist')(
            url,
            content,
            referer=referer,
        ),
    )
