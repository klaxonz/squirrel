"""Squirrel Crawl SDK

Light-weight SDK for building crawl / extraction plugins that can be loaded by
Squirrel backend and other Squirrel compatible runtimes.

Design principles:
- Protocol-based interfaces (structural typing)
- VideoMeta as the primary data model
- Unified plugin registry system
- Composition over inheritance
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version


def _detect_version() -> str:
    for dist_name in ("squirrel-sdk", "squirrel_sdk"):
        try:
            return _pkg_version(dist_name)  # type: ignore[arg-type]
        except PackageNotFoundError:
            continue
    # Development checkout – no installed distribution
    return "2.0.0.dev0"


__version__: str = _detect_version()

# Core interfaces and data models
from .interfaces import (
    TaskStatus,
    TaskPriority,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
    ActorMeta,
    Extractor,
    TaskProcessor,
    ResultHandler,
    Subscription,
    UserSubscriptionImporter,
    LoginStatusResult,
)

# Unified plugin registry system
from .plugin_registry import (
    PluginRegistry,
    get_extractor_registry,
    get_subscription_registry,
    get_importer_registry,
    get_login_checker_registry,
    reset_all_registries,
    ExtractorFactory,
    get_extractor_factory,
    register_extractor,
    register_subscription,
    register_user_subscription_importer,
    register_login_checker,
)

# Base classes (optional, for convenience)
from .plugin_base import BaseExtractor
from .video_extractor_base import (
    VideoExtractorBase,
    YoutubeDLExtractorBase,
)

# Utilities
from .meta_origin import SubscriptionMeta
from .utils import (
    filter_cookies_to_query_string,
    configure_cookie_file_resolver,
    resolve_cookie_file_path,
)

# HTTP utilities
from .http import (
    RateLimit,
    RateLimiter,
    RateLimitedSession,
    configure_rate_limit,
    get_rate_limiter,
    get_http_session,
    request,
    request_without_limit,
    get,
    post,
)

# Site configuration
from .site_config import (
    set_site_config,
    set_site_configs,
    get_site_config,
    get_http_headers,
    get_login_config,
    get_login_headers,
    get_proxy_config,
    get_rate_limit_config,
)

# Other plugin types (if needed)
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
    # Core interfaces
    "TaskStatus",
    "TaskPriority",
    "ExtractionTask",
    "ExtractionResult",
    "VideoMeta",
    "ActorMeta",
    "Extractor",
    "TaskProcessor",
    "ResultHandler",
    "Subscription",
    "UserSubscriptionImporter",
    "LoginStatusResult",
    # Registry system
    "PluginRegistry",
    "get_extractor_registry",
    "get_subscription_registry",
    "get_importer_registry",
    "get_login_checker_registry",
    "reset_all_registries",
    "ExtractorFactory",
    "get_extractor_factory",
    "register_extractor",
    "register_subscription",
    "register_user_subscription_importer",
    "register_login_checker",
    # Base classes
    "BaseExtractor",
    "VideoExtractorBase",
    "YoutubeDLExtractorBase",
    # Utilities
    "SubscriptionMeta",
    "filter_cookies_to_query_string",
    "configure_cookie_file_resolver",
    "resolve_cookie_file_path",
    # HTTP utilities
    "RateLimit",
    "RateLimiter",
    "RateLimitedSession",
    "configure_rate_limit",
    "get_rate_limiter",
    "get_http_session",
    "request",
    "request_without_limit",
    "get",
    "post",
    # Site configuration
    "set_site_config",
    "set_site_configs",
    "get_site_config",
    "get_http_headers",
    "get_login_config",
    "get_login_headers",
    "get_proxy_config",
    "get_rate_limit_config",
    # Other plugin types
    "VideoUrlHandler",
    "HandlerRegistry",
    "register_handler",
    "BaseMpdBuilder",
    "MpdRegistry",
    "register_mpd",
    "BaseSubtitlesProvider",
    "SubtitlesRegistry",
    "register_subtitles",
    "IdExtractor",
    "IdExtractorRegistry",
    "register_id_extractor",
    "VideoProxyBase",
    "ProxyRegistry",
    "register_proxy",
    "ProxyConfigProvider",
    "ProxyDomainConfig",
    "register_site_config",
    "BaseDownloader",
    "DownloaderRegistry",
    "DownloaderFactory",
    "get_downloader_factory",
    "register_downloader",
]
