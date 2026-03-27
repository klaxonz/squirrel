from __future__ import annotations

from typing import Any, Dict

from crawl import (
    PluginCapability,
    PluginHealthStatus,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
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
    ],
    sites=[
        PluginSiteManifest(
            site_name='bilibili',
            domains=['bilibili.com', 'b23.tv'],
            test_url='https://www.bilibili.com',
            features=['check_login_status', 'import_subscriptions'],
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
        },
        health_check=_health_check,
    )
