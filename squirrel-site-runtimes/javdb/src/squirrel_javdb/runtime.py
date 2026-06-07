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

DEFAULT_SITE_METADATA = {
    'label': 'JavDB',
    'aliases': [],
    'http': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    },
    'rate_limit': {
        'enabled': True,
        'min_interval': 5.0,
        'max_interval': 8.0,
    },
    'proxy': {
        'connect_timeout': 30.0,
        'read_timeout': 180.0,
        'write_timeout': 30.0,
        'pool_timeout': 30.0,
        'keepalive_expiry': 60.0,
        'max_connections': 40,
        'max_keepalive_connections': 20,
        'chunk_size': 2 * 1024 * 1024,
        'max_retries': 5,
        'enable_http2': True,
        'follow_redirects': True,
    },
    'login': {
        'check_url': 'https://javdb.com/users/collection_actors',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        },
        'timeout': 15.0,
    },
    'metadata': {
        'requires_cookies': True,
        'requires_login': True,
        'offline_thumbnails_download': True,
        'offline_thumbnails_display': False,
        'nsfw': True,
    },
}

SITE_RUNTIME_MANIFEST = SiteRuntimeManifest(
    runtime_id='javdb',
    version='0.1.0',
    display_name='JavDB',
    description='JavDB crawl integration',
    capabilities=[
        SiteRuntimeCapability(
            name='check_login_status',
            description='Check the current JavDB login state.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='import_subscriptions',
            description='Import followed JavDB actors for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        SiteRuntimeCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a JavDB actor URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a JavDB subscription.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        SiteRuntimeCapability(
            name='extract_video',
            description='Extract structured metadata for a JavDB video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        SiteRuntimeCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for JavDB streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        SiteRuntimeCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied JavDB playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        SiteRuntimeSite(
            site_name='javdb',
            domains=['javdb.com'],
            test_url='https://javdb.com',
            metadata=DEFAULT_SITE_METADATA,
            features=[
                'check_login_status',
                'import_subscriptions',
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'resolve_proxy_config',
                'rewrite_proxy_playlist',
            ],
        )
    ],
    permissions=[
        SiteRuntimePermission(
            name='network:http',
            description='Access JavDB APIs and mirrored web pages over HTTP.',
        ),
        SiteRuntimePermission(
            name='cookies:read:site/javdb',
            description='Read JavDB cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def get_site_runtime():
    return create_site_runtime(
        manifest=SITE_RUNTIME_MANIFEST,
        health_message='JavDB runtime is configured',
        check_login=lambda: _load_local_attr('auth', 'check_javdb_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'JavdbUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'JavdbSubscription')(url=url),
        extractor_factory=lambda: _load_local_attr('extractor', 'JavdbExtractor')(),
        extractor_site_name='javdb',
        proxy_config_builder=lambda payload: _load_local_attr('proxy', 'build_runtime_proxy_config')(payload),
        playlist_rewriter=lambda url, content, referer=None: _load_local_attr('proxy', 'rewrite_proxy_playlist')(
            url,
            content,
            referer=referer,
        ),
    )
