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
            timeout_ms=120000,
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
        PluginCapability(
            name='resolve_proxy_config',
            description='Resolve proxy headers and transport settings for Pornhub streams.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
        ),
        PluginCapability(
            name='rewrite_proxy_playlist',
            description='Rewrite proxied Pornhub playlists to point back to the backend proxy.',
            response_schema={'type': 'object'},
            timeout_ms=15000,
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
                'resolve_proxy_config',
                'rewrite_proxy_playlist',
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


def get_plugin_runtime():
    return create_site_runtime(
        manifest=PLUGIN_MANIFEST,
        health_message='Pornhub runtime is configured',
        check_login=lambda: _load_local_attr('auth', 'check_pornhub_login_status')(),
        importer_factory=lambda: _load_local_attr('importer', 'PornhubUserSubscriptionImporter')(),
        subscription_factory=lambda url: _load_local_attr('subscription', 'PornhubSubscription')(url=url),
        extractor_factory=lambda: _load_local_attr('extractor', 'PornhubExtractor')(),
        extractor_site_name='pornhub',
        playback_handler_factory=lambda: _load_local_attr('handler', 'PornhubHandler')(),
        proxy_config_builder=lambda domain: _load_local_attr('proxy', 'build_runtime_proxy_config')(domain),
        playlist_rewriter=lambda url, content, referer=None: _load_local_attr('proxy', 'rewrite_proxy_playlist')(
            url,
            content,
            referer=referer,
        ),
    )
