"""Pornhub crawl plugin for Squirrel."""

from .handler import PornhubHandler  # noqa: F401
from .subscription import PornhubSubscription  # noqa: F401
from .id_extractor import PornhubIdExtractor  # noqa: F401
from .extractor import PornhubExtractor  # noqa: F401
from .config import PornhubProxyConfig  # noqa: F401
from .proxy import PornhubProxy  # noqa: F401
from .importer import PornhubUserSubscriptionImporter  # noqa: F401
from . import auth as _auth  # noqa: F401


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


