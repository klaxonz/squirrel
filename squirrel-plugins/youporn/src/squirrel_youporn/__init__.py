"""YouPorn crawl plugin for Squirrel."""

PLUGIN_NAME = 'youporn'
PLUGIN_VERSION = '0.1.0'
PLUGIN_DESCRIPTION = 'YouPorn crawl integration'

__all__ = [
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_DESCRIPTION',
    'get_plugin_runtime',
]


def get_plugin_runtime():
    from .runtime import get_plugin_runtime as _get_plugin_runtime

    return _get_plugin_runtime()
