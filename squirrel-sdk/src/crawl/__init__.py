"""Squirrel Crawl SDK

Light-weight SDK for building crawl / extraction plugins that can be loaded by
Squirrel backend and other Squirrel compatible runtimes.

Only pure-python stdlib dependencies are used to maximise portability.
"""

# `squirrel-sdk` is distributed as a **single wheel**; crawl is a sub-package.
# Keep version aligned with the root package instead of using a fictitious
# "squirrel-sdk-crawl" distribution.
from importlib.metadata import PackageNotFoundError, version as _pkg_version


def _detect_version() -> str:
    for dist_name in ("squirrel-sdk", "squirrel_sdk"):
        try:
            return _pkg_version(dist_name)  # type: ignore[arg-type]
        except PackageNotFoundError:
            continue
    # Development checkout – no installed distribution
    return "0.1.0.dev0"


__version__: str = _detect_version()

from .interfaces import (
    TaskStatus,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
    IExtractor,
    ITaskProcessor,
    IResultHandler,
    TaskPriority,
)
from .registry import (
    ExtractorRegistry,
    register_extractor,
    get_extractor_factory,
    SubscriptionRegistry,
    SubscriptionFactory,
    register_subscription,
)
from .meta_origin import Video, Actor, SubscriptionMeta
from .utils import filter_cookies_to_query_string
from .meta_registry import MetaRegistry, register_meta, VideoFactory
from .handler_interfaces import VideoUrlHandler, HandlerRegistry, register_handler
from .mpd_interfaces import BaseMpdBuilder, MpdRegistry, register_mpd
from .subtitles_interfaces import BaseSubtitlesProvider, SubtitlesRegistry, register_subtitles
from .id_extractor_interfaces import IdExtractor, IdExtractorRegistry, register_extractor as register_id_extractor
from .proxy_interfaces import (
    VideoProxyBase,
    ProxyRegistry,
    register_proxy,
    ProxyConfigProvider,
    ProxyDomainConfig,
    register_site_config,
)
from .downloader_interfaces import (
    BaseDownloader,
    DownloaderRegistry,
    DownloaderFactory,
    get_downloader_factory,
    register_downloader,
)

__all__ = [
    "__version__",
    # interfaces
    "TaskStatus",
    "ExtractionTask",
    "ExtractionResult",
    "VideoMeta",
    "TaskPriority",
    "IExtractor",
    "ITaskProcessor",
    "IResultHandler",
    # base entities
    "Video",
    "Actor",
    "SubscriptionMeta",
    # registry helpers
    "ExtractorRegistry",
    "register_extractor",
    "get_extractor_factory",
    "BaseExtractor",
    # subscription
    "SubscriptionRegistry",
    "SubscriptionFactory",
    "register_subscription",
    # utils
    "filter_cookies_to_query_string",
    # meta & factory
    "MetaRegistry",
    "register_meta",
    "VideoFactory",
    # handlers
    "VideoUrlHandler",
    "HandlerRegistry",
    "register_handler",
    # mpd
    "BaseMpdBuilder",
    "MpdRegistry",
    "register_mpd",
    # subtitles
    "BaseSubtitlesProvider",
    "SubtitlesRegistry",
    "register_subtitles",
    # id extractor
    "IdExtractor",
    "IdExtractorRegistry",
    "register_id_extractor",
    # proxy
    "VideoProxyBase",
    "ProxyRegistry",
    "register_proxy",
    # downloader
    "BaseDownloader",
    "DownloaderRegistry",
    "DownloaderFactory",
    "get_downloader_factory",
    "register_downloader",
]

# Re-export for convenience
from .plugin_base import BaseExtractor  # noqa: E402  (import after __all__ definition)
