"""Pornhub crawl plugin for Squirrel."""

from .handler import PornhubHandler  # noqa: F401
from .subscription import PornhubSubscription  # noqa: F401
from .id_extractor import PornhubIdExtractor  # noqa: F401
from .meta import PornhubVideo  # noqa: F401


PLUGIN_NAME = "pornhub"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "Pornhub crawl integration"

try:
    from plugins.registry import register_plugin

    @register_plugin
    class PornhubPlugin:
        name = PLUGIN_NAME
        version = PLUGIN_VERSION
        description = PLUGIN_DESCRIPTION

        def on_load(self):
            pass

except ImportError:
    pass


