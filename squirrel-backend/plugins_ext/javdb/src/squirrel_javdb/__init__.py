"""JavDB crawl plugin for Squirrel."""

from .handler import JavdbHandler  # noqa: F401
from .subscription import JavdbSubscription  # noqa: F401
from .id_extractor import JavdbIdExtractor  # noqa: F401


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


