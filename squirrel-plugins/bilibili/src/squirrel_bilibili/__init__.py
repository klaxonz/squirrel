"""Bilibili crawl plugin for Squirrel."""

from .subscription import BilibiliSubscription  # noqa: F401
from .meta import BilibiliVideo  # noqa: F401
from .handler import BilibiliHandler  # noqa: F401
from .mpd import BilibiliMpdBuilder  # noqa: F401
from .subtitles import BilibiliSubtitlesProvider  # noqa: F401
from .id_extractor import BilibiliIdExtractor  # noqa: F401
from .downloader import BilibiliDownloader  # noqa: F401
from .config import BilibiliProxyConfig  # noqa: F401
from .extractor import BilibiliExtractor  # noqa: F401
from .importer import BilibiliUserSubscriptionImporter  # noqa: F401
from . import auth as _auth  # noqa: F401

PLUGIN_NAME = "bilibili"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "Bilibili crawl integration"

try:
    from plugins.registry import register_plugin

    @register_plugin
    class BilibiliPlugin:
        name = PLUGIN_NAME
        version = PLUGIN_VERSION
        description = PLUGIN_DESCRIPTION

        def on_load(self):
            pass

except ImportError:
    pass


