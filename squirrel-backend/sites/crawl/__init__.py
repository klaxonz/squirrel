"""Squirrel crawl runtime helpers.

Shared runtime contracts and helpers for first-party site runtimes.

Design principles:
- Runtime V2 first
- Protocol-based interfaces (structural typing)
- VideoMeta as the primary data model
- Composition over inheritance
"""


__version__: str = "2.0.0"

# Site runtime API
# Auth base
from .auth_base import check_login_status

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
    ExtractionResult,
    ExtractionTask,
    TaskPriority,
    Extractor,
    LoginStatusResult,
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    VideoMeta,
)

# Exceptions
from .exceptions import (
    AuthError,
    ErrorCategory,
    NetworkError,
    NotFoundError,
    ParseError,
    SiteError,
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
from .subscription_helpers import (
    HEAD_SAMPLE_LIMIT,
    append_subscription_video_url,
    build_page_url,
    build_subscription_sync_result,
    count_page_unique_videos,
    resolve_count_offset,
    resolve_page,
    resolve_previous_page_urls,
    resolve_subscription_limit,
)

# Other protocol-based interfaces
from .utils import (
    META_THUMBNAIL_PATTERNS,
    build_cookie_header,
    configure_cookie_domain_resolver,
    configure_cookie_file_resolver,
    fetch_page_thumbnail_url,
    filter_cookies_to_query_string,
    looks_like_expiring_preview_thumbnail,
    normalize_thumbnail,
    pick_best_thumbnail_url,
    resolve_cookie_file_path,
)
from .ytdlp import apply_ytdlp_rate_limit

__all__ = [
    "__version__",
    # Core interfaces
    "ExtractionTask",
    "TaskPriority",
    "ExtractionResult",
    "VideoMeta",
    "SubscriptionImportItem",
    "SubscriptionImportBatchResult",
    "Extractor",
    "LoginStatusResult",
    # Base classes
    "VideoExtractorBase",
    "YoutubeDLExtractorBase",
    # Utilities
    "SubscriptionMeta",
    "SubscriptionSyncContext",
    "SubscriptionSyncResult",
    "filter_cookies_to_query_string",
    "configure_cookie_domain_resolver",
    "configure_cookie_file_resolver",
    "resolve_cookie_file_path",
    "append_subscription_video_url",
    "build_subscription_sync_result",
    "resolve_subscription_limit",
    "HEAD_SAMPLE_LIMIT",
    # Shared helpers
    "resolve_page",
    "build_page_url",
    "resolve_count_offset",
    "resolve_previous_page_urls",
    "count_page_unique_videos",
    "META_THUMBNAIL_PATTERNS",
    "looks_like_expiring_preview_thumbnail",
    "pick_best_thumbnail_url",
    "normalize_thumbnail",
    "build_cookie_header",
    "fetch_page_thumbnail_url",
    # HTTP utilities
    "RateLimit",
    "RateLimiter",
    "RateLimitedSession",
    "configure_rate_limit",
    "configure_rate_limit_enabled",
    "get_rate_limiter",
    "get_http_session",
    "request",
    "request_without_limit",
    "get",
    "post",
    "configure_cloudflare_bypass_client",
    "apply_ytdlp_rate_limit",
    "check_login_status",
    # Site configuration
    "set_site_config",
    "set_site_configs",
    "get_site_config",
    "get_http_headers",
    "get_login_config",
    "get_login_headers",
    "get_proxy_config",
    "get_rate_limit_config",
    # Other protocol-based interfaces
    "IdExtractor",
    "RegexIdExtractor",
    # Exceptions
    "ErrorCategory",
    "SiteError",
    "NetworkError",
    "RateLimitError",
    "AuthError",
    "VipError",
    "NotFoundError",
    "ParseError",
    # Importer base classes
]
