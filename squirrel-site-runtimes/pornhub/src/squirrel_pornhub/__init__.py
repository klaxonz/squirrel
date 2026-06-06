"""Pornhub crawl plugin for Squirrel."""

from .runtime import get_site_runtime

PLUGIN_NAME = 'pornhub'
PLUGIN_VERSION = '0.1.0'
PLUGIN_DESCRIPTION = 'Pornhub crawl integration'

__all__ = [
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_DESCRIPTION',
    'get_site_runtime',
]


