"""JavDB crawl plugin for Squirrel."""

from __future__ import annotations

from .handler import JavdbHandler  # noqa: F401
from .subscription import JavdbSubscription  # noqa: F401
from .id_extractor import JavdbIdExtractor  # noqa: F401
from .meta import JavdbVideo  # noqa: F401
from .downloader import JavdbDownloader  # noqa: F401
from .proxy import JavdbProxy  # noqa: F401
from .config import JavdbProxyConfig  # noqa: F401
from .extractor import JavdbExtractor  # noqa: F401
from .importer import JavdbUserSubscriptionImporter  # noqa: F401


PLUGIN_NAME = "javdb"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "JavDB crawl integration"

try:
    from plugins.registry import register_plugin

    @register_plugin
    class JavdbPlugin:
        name = PLUGIN_NAME
        version = PLUGIN_VERSION
        description = PLUGIN_DESCRIPTION

        def on_load(self):
            pass

except ImportError:
    pass


