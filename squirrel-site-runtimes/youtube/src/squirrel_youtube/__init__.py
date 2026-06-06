"""YouTube crawl plugin for Squirrel."""

from .runtime import get_site_runtime

PLUGIN_NAME = 'youtube'
PLUGIN_VERSION = '0.1.0'
PLUGIN_DESCRIPTION = 'YouTube crawl integration'

__all__ = [
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_DESCRIPTION',
    'get_site_runtime',
]


