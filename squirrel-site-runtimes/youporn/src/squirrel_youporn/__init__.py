"""YouPorn crawl plugin for Squirrel."""

PLUGIN_NAME = "youporn"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "YouPorn crawl integration"

__all__ = [
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "PLUGIN_DESCRIPTION",
    "get_site_runtime",
]


def get_site_runtime():
    from .runtime import get_site_runtime as _get_site_runtime

    return _get_site_runtime()
