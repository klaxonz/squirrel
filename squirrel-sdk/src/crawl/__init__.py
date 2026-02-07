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
from .core import (
    TaskStatus,
    TaskPriority,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
    ActorMeta,
    SubscriptionImportItem,
    Extractor,
    TaskProcessor,
    ResultHandler,
    Subscription,
    UserSubscriptionImporter,
    LoginStatusResult,
    SubscriptionMeta,
)

# Unified plugin registry system
from .registries import (
    PluginRegistry,
    ComponentFactory,
    RegistryManager,
    get_registry_manager,
    reset_registry_manager,
)
from .registry import (
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
from .base import BaseExtractor
from .extractor import (
    VideoExtractorBase,
    YoutubeDLExtractorBase,
)
from .utils import (
    filter_cookies_to_query_string,
    configure_cookie_file_resolver,
    resolve_cookie_file_path,
)

# Exceptions
from .exceptions import (
    ErrorCategory,
    PluginError,
    NetworkError,
    RateLimitError,
    AuthError,
    VipError,
    NotFoundError,
    ParseError,
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
    configure_cloudflare_bypass_client
)

# Proxy provider
from .proxy_provider import (
    ProxyInfo,
    ProxyProvider,
    configure_proxy_provider,
    get_proxy_provider,
)

# Site configuration
from .config import (
    set_site_config,
    set_site_configs,
    get_site_config,
    get_http_headers,
    get_login_config,
    get_login_headers,
    get_proxy_config,
    get_rate_limit_config,
)

# Other plugin types (Protocol-based interfaces with unified registry)
from .url_handler import (
    VideoUrlHandler,
    get_handler_registry,
    register_handler,
)
from .mpd import (
    MpdBuilder,
    get_mpd_registry,
    register_mpd,
)
from .subtitles import (
    SubtitlesProvider,
    get_subtitles_registry,
    register_subtitles,
)
from .id_extractor import (
    IdExtractor,
    RegexIdExtractor,
    get_id_extractor_registry,
    register_id_extractor,
)
from .proxy import (
    VideoProxy,
    get_proxy_registry,
    register_proxy,
    ProxyConfigProvider,
    ProxyDomainConfig,
    get_proxy_config_registry,
    register_site_config,
    create_site_config,
)
from .downloader import (
    Downloader,
    get_downloader_registry,
    DownloaderFactory,
    get_downloader_factory,
    register_downloader,
)
from .importer import (
    BaseImporter,
    PaginatedImporter,
)

# Plugin descriptor for declarative plugin configuration
from .plugin import (
    PluginDescriptor,
    create_plugin,
    discover_components,
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
    "SubscriptionImportItem",
    "Extractor",
    "TaskProcessor",
    "ResultHandler",
    "Subscription",
    "UserSubscriptionImporter",
    "LoginStatusResult",
    # Registry system
    "PluginRegistry",
    "ComponentFactory",
    "RegistryManager",
    "get_registry_manager",
    "reset_registry_manager",
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
    "configure_cloudflare_bypass_client",
    # Proxy provider
    "ProxyInfo",
    "ProxyProvider",
    "configure_proxy_provider",
    "get_proxy_provider",
    # Site configuration
    "set_site_config",
    "set_site_configs",
    "get_site_config",
    "get_http_headers",
    "get_login_config",
    "get_login_headers",
    "get_proxy_config",
    "get_rate_limit_config",
    # Other plugin types (Protocol-based)
    "VideoUrlHandler",
    "get_handler_registry",
    "register_handler",
    "MpdBuilder",
    "get_mpd_registry",
    "register_mpd",
    "SubtitlesProvider",
    "get_subtitles_registry",
    "register_subtitles",
    "IdExtractor",
    "RegexIdExtractor",
    "get_id_extractor_registry",
    "register_id_extractor",
    "VideoProxy",
    "get_proxy_registry",
    "register_proxy",
    "ProxyConfigProvider",
    "ProxyDomainConfig",
    "get_proxy_config_registry",
    "register_site_config",
    "create_site_config",
    "Downloader",
    "get_downloader_registry",
    "DownloaderFactory",
    "get_downloader_factory",
    "register_downloader",
    # Exceptions
    "ErrorCategory",
    "PluginError",
    "NetworkError",
    "RateLimitError",
    "AuthError",
    "VipError",
    "NotFoundError",
    "ParseError",
    # Importer base classes
    "BaseImporter",
    "PaginatedImporter",
    # Plugin descriptor
    "PluginDescriptor",
    "create_plugin",
    "discover_components",
]
