from __future__ import annotations

from importlib import import_module

from crawl import (
    PluginCapability,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
    create_site_runtime,
)


def _load_local_attr(module_name: str, attr_name: str):
    return getattr(import_module(f'{__package__}.{module_name}'), attr_name)


DEFAULT_SITE_METADATA = {
    'label': 'YouPorn',
    'aliases': ['yp'],
    'http': {
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youporn.com',
        }
    },
    'rate_limit': {
        'enabled': True,
        'min_interval': 3.0,
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
        'check_url': 'https://www.youporn.com/',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'timeout': 20.0,
    },
    'metadata': {
        'requires_cookies': True,
        'requires_login': False,
        'nsfw': True,
    },
}


PLUGIN_MANIFEST = PluginManifest(
    plugin_id='youporn',
    version='0.1.0',
    display_name='YouPorn',
    description='YouPorn crawl integration',
    capabilities=[
        PluginCapability(
            name='check_login_status',
            description='Check the current YouPorn login state.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='import_subscriptions',
            description='Import followed YouPorn creators for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a YouPorn channel or pornstar URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a YouPorn channel or pornstar page.',
            response_schema={'type': 'object'},
            timeout_ms=120000,
        ),
        PluginCapability(
            name='extract_video',
            description='Extract structured metadata for a YouPorn video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_playback',
            description='Resolve playback URLs for a YouPorn video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for YouPorn streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied YouPorn playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        PluginSiteManifest(
            site_name='youporn',
            domains=['youporn.com'],
            test_url='https://www.youporn.com',
            metadata=DEFAULT_SITE_METADATA,
            features=[
                'check_login_status',
                'import_subscriptions',
                'resolve_subscription',
                'sync_subscription',
                'extract_video',
                'resolve_playback',
                'resolve_proxy_config',
                'rewrite_proxy_playlist',
            ],
        )
    ],
    permissions=[
        PluginPermission(
            name='network:http',
            description='Access YouPorn APIs and web pages over HTTP.',
        ),
        PluginPermission(
            name='cookies:read:site/youporn',
            description='Read YouPorn cookies for authenticated requests when available.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def get_plugin_runtime():
    return create_site_runtime(
        manifest=PLUGIN_MANIFEST,
        health_message='YouPorn runtime is configured',
        check_login=lambda: _load_local_attr('auth', 'check_youporn_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'YouPornUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'YouPornSubscription')(url=url),
        extractor_factory=lambda: _load_local_attr('extractor', 'YouPornExtractor')(),
        extractor_site_name='youporn',
        playback_handler_factory=lambda: _load_local_attr('handler', 'YouPornHandler')(),
        proxy_config_builder=lambda domain: _load_local_attr('proxy', 'build_runtime_proxy_config')(domain),
        playlist_rewriter=lambda url, content, referer=None: _load_local_attr('proxy', 'rewrite_proxy_playlist')(
            url,
            content,
            referer=referer,
        ),
    )
