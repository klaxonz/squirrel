"""YouTube crawl plugin for Squirrel."""

from __future__ import annotations

from .handler import YouTubeHandler  # noqa: F401
from .subscription import YoutubeSubscription  # noqa: F401
from .id_extractor import YoutubeIdExtractor  # noqa: F401
from .meta import YoutubeVideo  # noqa: F401
from .mpd import YouTubeMpdBuilder  # noqa: F401
from .subtitles import YoutubeSubtitlesProvider  # noqa: F401
from .extractor import YoutubeExtractor  # noqa: F401


PLUGIN_NAME = "youtube"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "YouTube crawl integration"

try:
    from plugins.registry import register_plugin

    @register_plugin
    class YoutubePlugin:
        name = PLUGIN_NAME
        version = PLUGIN_VERSION
        description = PLUGIN_DESCRIPTION

        def on_load(self):
            pass

except ImportError:
    pass


