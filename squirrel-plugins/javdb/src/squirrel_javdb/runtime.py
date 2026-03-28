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

PLUGIN_MANIFEST = PluginManifest(
    plugin_id='javdb',
    version='0.1.0',
    display_name='JavDB',
    description='JavDB crawl integration',
    capabilities=[
        PluginCapability(
            name='check_login_status',
            description='Check the current JavDB login state.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='import_subscriptions',
            description='Import followed JavDB actors for the current account.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_subscription',
            description='Resolve subscription metadata for a JavDB actor URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='sync_subscription',
            description='Fetch subscription video URLs for a JavDB subscription.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='extract_video',
            description='Extract structured metadata for a JavDB video URL.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_playback',
            description='Resolve playback URLs for a JavDB video.',
            response_schema={'type': 'object'},
            timeout_ms=30000,
        ),
        PluginCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for JavDB streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied JavDB playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
    ],
    sites=[
        PluginSiteManifest(
            site_name='javdb',
            domains=['javdb.com'],
            test_url='https://javdb.com',
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
            description='Access JavDB APIs and mirrored web pages over HTTP.',
        ),
        PluginPermission(
            name='cookies:read:site/javdb',
            description='Read JavDB cookies for authenticated requests.',
        ),
    ],
    health_policy={'startup_timeout_ms': 10000},
)


def get_plugin_runtime():
    return create_site_runtime(
        manifest=PLUGIN_MANIFEST,
        health_message='JavDB runtime is configured',
        check_login=lambda: _load_local_attr('auth', 'check_javdb_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'JavdbUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'JavdbSubscription')(url=url),
        extractor_factory=lambda: _load_local_attr('extractor', 'JavdbExtractor')(),
        extractor_site_name='javdb',
        playback_handler_factory=lambda: _load_local_attr('handler', 'JavdbHandler')(),
        proxy_config_builder=lambda domain: _load_local_attr('proxy', 'build_runtime_proxy_config')(domain),
        playlist_rewriter=lambda url, content, referer=None: _load_local_attr('proxy', 'rewrite_proxy_playlist')(
            url,
            content,
            referer=referer,
        ),
    )
