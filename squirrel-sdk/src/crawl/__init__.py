"""Squirrel Crawl SDK

Light-weight SDK for building crawl / extraction plugins that can be loaded by
Squirrel backend and other Squirrel compatible runtimes.

Design principles:
- Runtime V2 first
- Protocol-based interfaces (structural typing)
- VideoMeta as the primary data model
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

# Runtime V2 plugin API
from .runtime_errors import (
    RuntimeErrorCode,
    PluginRuntimeError,
)
from .runtime_models import (
    PluginCapability,
    PluginHealthStatus,
    PluginInvokeRequest,
    PluginInvokeResponse,
    PluginManifest,
    PluginPermission,
    PluginSiteManifest,
)
from .runtime_protocol import (
    PluginRuntime,
    PluginRuntimeFactory,
)
from .plugin import create_plugin_runtime
from .runtime_helpers import create_site_runtime
from .proxy_helpers import (
    build_proxy_config_values,
    build_runtime_proxy_config,
    safe_cookie_header_value,
)
from .playlist_rewrite import (
    rewrite_playlist_for_proxy,
    rewrite_proxy_playlist_content,
)
from .subscription_helpers import (
    append_subscription_video_url,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

# Core interfaces and data models
from .core import (
    TaskStatus,
    TaskPriority,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
    ActorMeta,
    SubscriptionImportItem,
    SubscriptionImportBatchResult,
    Extractor,
    TaskProcessor,
    ResultHandler,
    Subscription,
    UserSubscriptionImporter,
    PaginatedUserSubscriptionImporter,
    LoginStatusResult,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
)

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
    configure_rate_limit_enabled,
    get_rate_limiter,
    get_http_session,
    request,
    request_without_limit,
    get,
    post,
    configure_cloudflare_bypass_client
)
from .ytdlp import apply_ytdlp_rate_limit

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

# Other plugin types (Protocol-based interfaces)
from .url_handler import (
    VideoUrlHandler,
)
from .mpd import (
    MpdBuilder,
)
from .subtitles import (
    SubtitlesProvider,
)
from .id_extractor import (
    IdExtractor,
    RegexIdExtractor,
)
from .proxy import (
    VideoProxy,
    ProxyConfigProvider,
    ProxyDomainConfig,
)
from .importer import (
    BaseImporter,
    PaginatedImporter,
)

__all__ = [
    '__version__',
    # Runtime V2 API
    'RuntimeErrorCode',
    'PluginRuntimeError',
    'PluginCapability',
    'PluginHealthStatus',
    'PluginInvokeRequest',
    'PluginInvokeResponse',
    'PluginManifest',
    'PluginPermission',
    'PluginSiteManifest',
    'PluginRuntime',
    'PluginRuntimeFactory',
    'create_plugin_runtime',
    'create_site_runtime',
    # Core interfaces
    'TaskStatus',
    'TaskPriority',
    'ExtractionTask',
    'ExtractionResult',
    'VideoMeta',
    'ActorMeta',
    'SubscriptionImportItem',
    'SubscriptionImportBatchResult',
    'Extractor',
    'TaskProcessor',
    'ResultHandler',
    'Subscription',
    'UserSubscriptionImporter',
    'PaginatedUserSubscriptionImporter',
    'LoginStatusResult',
    # Base classes
    'VideoExtractorBase',
    'YoutubeDLExtractorBase',
    # Utilities
    'SubscriptionMeta',
    'SubscriptionSyncContext',
    'SubscriptionSyncResult',
    'filter_cookies_to_query_string',
    'configure_cookie_file_resolver',
    'resolve_cookie_file_path',
    'build_proxy_config_values',
    'build_runtime_proxy_config',
    'safe_cookie_header_value',
    'rewrite_playlist_for_proxy',
    'rewrite_proxy_playlist_content',
    'append_subscription_video_url',
    'build_subscription_sync_result',
    'resolve_subscription_limit',
    # HTTP utilities
    'RateLimit',
    'RateLimiter',
    'RateLimitedSession',
    'configure_rate_limit',
    'configure_rate_limit_enabled',
    'get_rate_limiter',
    'get_http_session',
    'request',
    'request_without_limit',
    'get',
    'post',
    'configure_cloudflare_bypass_client',
    'apply_ytdlp_rate_limit',
    # Site configuration
    'set_site_config',
    'set_site_configs',
    'get_site_config',
    'get_http_headers',
    'get_login_config',
    'get_login_headers',
    'get_proxy_config',
    'get_rate_limit_config',
    # Other plugin types (Protocol-based)
    'VideoUrlHandler',
    'MpdBuilder',
    'SubtitlesProvider',
    'IdExtractor',
    'RegexIdExtractor',
    'VideoProxy',
    'ProxyConfigProvider',
    'ProxyDomainConfig',
    # Exceptions
    'ErrorCategory',
    'PluginError',
    'NetworkError',
    'RateLimitError',
    'AuthError',
    'VipError',
    'NotFoundError',
    'ParseError',
    # Importer base classes
    'BaseImporter',
    'PaginatedImporter',
]
