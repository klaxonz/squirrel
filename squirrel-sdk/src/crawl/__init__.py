"""Squirrel Crawl SDK

Light-weight SDK for building crawl / extraction plugins that can be loaded by
Squirrel backend and other Squirrel compatible runtimes.

Design principles:
- Runtime V2 first
- Protocol-based interfaces (structural typing)
- VideoMeta as the primary data model
- Composition over inheritance
"""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version


def _detect_version() -> str:
    for dist_name in ("squirrel-sdk", "squirrel_sdk"):
        try:
            return _pkg_version(dist_name)  # type: ignore[arg-type]
        except PackageNotFoundError:
            continue
    # Development checkout – no installed distribution
    return "2.0.0.dev0"


__version__: str = _detect_version()

# Site runtime API
# Site configuration
from .config import (
    get_http_headers,
    get_login_config,
    get_login_headers,
    get_proxy_config,
    get_rate_limit_config,
    get_site_config,
    set_site_config,
    set_site_configs,
)

# Core interfaces and data models
from .core import (
    ActorMeta,
    ExtractionResult,
    ExtractionTask,
    Extractor,
    LoginStatusResult,
    PaginatedUserSubscriptionImporter,
    ResultHandler,
    Subscription,
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    TaskPriority,
    TaskProcessor,
    TaskStatus,
    UserSubscriptionImporter,
    VideoMeta,
)

# Exceptions
from .exceptions import (
    AuthError,
    ErrorCategory,
    NetworkError,
    NoSubtitlesError,
    NotFoundError,
    ParseError,
    PluginError,
    RateLimitError,
    VipError,
)
from .extractor import (
    VideoExtractorBase,
    YoutubeDLExtractorBase,
)

# HTTP utilities
from .http import (
    RateLimit,
    RateLimitedSession,
    RateLimiter,
    configure_cloudflare_bypass_client,
    configure_rate_limit,
    configure_rate_limit_enabled,
    get,
    get_http_session,
    get_rate_limiter,
    post,
    request,
    request_without_limit,
)
from .id_extractor import (
    IdExtractor,
    RegexIdExtractor,
)
from .importer import (
    BaseImporter,
    PaginatedImporter,
)
from .playlist_rewrite import (
    rewrite_playlist_for_proxy,
    rewrite_proxy_playlist_content,
)
from .proxy import (
    ProxyConfigProvider,
    ProxyDomainConfig,
    VideoProxy,
)
from .proxy_helpers import (
    build_proxy_config_values,
    build_runtime_proxy_config,
    safe_cookie_header_value,
)
from .runtime_errors import (
    RuntimeErrorCode,
    SiteRuntimeError,
)
from .runtime_helpers import create_site_runtime
from .runtime_models import (
    SiteRuntimeCapability,
    SiteRuntimeHealthStatus,
    SiteRuntimeInvokeRequest,
    SiteRuntimeInvokeResponse,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeSite,
)
from .runtime_protocol import (
    SiteRuntime,
    SiteRuntimeFactory,
)
from .subscription_helpers import (
    append_subscription_video_url,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

# Other plugin types (Protocol-based interfaces)
from .subtitles import (
    SubtitlesProvider,
)
from .utils import (
    configure_cookie_domain_resolver,
    configure_cookie_file_resolver,
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
)
from .ytdlp import apply_ytdlp_rate_limit

__all__ = [
    '__version__',
    # Site runtime API
    'RuntimeErrorCode',
    'SiteRuntimeError',
    'SiteRuntimeCapability',
    'SiteRuntimeHealthStatus',
    'SiteRuntimeInvokeRequest',
    'SiteRuntimeInvokeResponse',
    'SiteRuntimeManifest',
    'SiteRuntimePermission',
    'SiteRuntimeSite',
    'SiteRuntime',
    'SiteRuntimeFactory',
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
    'configure_cookie_domain_resolver',
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
    'NoSubtitlesError',
    # Importer base classes
    'BaseImporter',
    'PaginatedImporter',
]
