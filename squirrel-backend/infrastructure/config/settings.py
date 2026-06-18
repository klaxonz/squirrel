"""Application settings.

Structure:
- Sub-settings groups (RedisSettings, PostgresSettings, ...) are independent
  ``BaseSettings`` subclasses that read their own ``env_prefix``'d variables
  (e.g. ``REDIS_HOST`` → ``settings.redis.host``). They are exposed on the
  top-level ``Settings`` via cached properties so flat env-var names keep
  working without nested-delimiter gymnastics.
- The top-level ``Settings`` holds the remaining flat (ungrouped) fields.
- ``settings`` is a lazily-resolved module attribute (PEP 562): importing
  this module does not read env; the first ``settings.X`` access does.
"""
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Backend project root directory (module-level for convenience)
base_dir = Path(__file__).parent.parent.parent


def _env() -> str:
    """Current environment name (default 'prod')."""
    return os.getenv("ENV", "prod").lower()


# --------------------------------------------------------------------------- #
# Grouped sub-settings — each reads its own env-prefixed vars.
# --------------------------------------------------------------------------- #


class RedisSettings(BaseSettings):
    """Redis connection settings (env prefix ``REDIS_``)."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file_encoding="utf-8", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    max_connections: int = 256
    pool_timeout: int = 10

    @property
    def url(self) -> str:
        return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"


class PostgresSettings(BaseSettings):
    """PostgreSQL connection + connection-pool settings (env prefix ``POSTGRES_``)."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file_encoding="utf-8", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "squirrel"
    pool_size: int = 30
    pool_max_size: int = 60
    pool_recycle: int = 300

    @field_validator("password", mode="after")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if _env() != "dev" and v == "postgres":
            raise ValueError(
                "POSTGRES_PASSWORD must be changed from the default 'postgres' "
                "in non-dev environments. Set it via environment variable or .env file."
            )
        return v

    @property
    def url(self) -> str:
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class MeiliSettings(BaseSettings):
    """Meilisearch full-text search settings (env prefix ``MEILISEARCH_``).

    Search is disabled when ``url`` is empty; browse/detail remain unaffected.
    """

    model_config = SettingsConfigDict(env_prefix="MEILISEARCH_", env_file_encoding="utf-8", extra="ignore")

    url: str = ""
    key: str = ""
    index_videos: str = "videos"


class CrawlSettings(BaseSettings):
    """Crawl dispatcher / worker concurrency settings (env prefix ``CRAWL_``)."""

    model_config = SettingsConfigDict(env_prefix="CRAWL_", env_file_encoding="utf-8", extra="ignore")

    default_site_concurrency: int = 2
    # Plain key→int mappings; loaded from JSON env vars by pydantic-settings
    # (e.g. CRAWL_TASK_TYPE_LIMITS='{"video_extract": 8}').
    site_concurrency_overrides: dict[str, int] = {}
    task_type_limits: dict[str, int] = {
        "subscription_sync_incremental": 2,
        "subscription_sync_full": 1,
        "video_extract": 8,
    }
    slots_per_process: int = 8
    worker_lease_seconds: int = 60
    worker_poll_interval_ms: int = 1000
    # NOTE: full_sync_* and channel_update_default_size intentionally live on
    # the top-level Settings rather than here — their env-var names
    # (FULL_SYNC_MAX_INFLIGHT, CHANNEL_UPDATE_DEFAULT_SIZE) carry no CRAWL_
    # prefix, so grouping them under the CRAWL_ prefix would break existing
    # .env files.


class MqSettings(BaseSettings):
    """Redis-Stream message-queue consumer settings (env prefix ``MQ_``)."""

    model_config = SettingsConfigDict(env_prefix="MQ_", env_file_encoding="utf-8", extra="ignore")

    consumer_default_count: int = 1
    # Kept as a raw string because the runner parser supports ``stream*=N``
    # wildcard prefix matching (see WorkerRunner._parse_consumer_count_overrides),
    # which a plain dict cannot express.
    consumer_count_overrides: str = ""


class CookieCloudSettings(BaseSettings):
    """CookieCloud sync settings (env prefix ``COOKIECLOUD_``).

    CookieCloud sync is disabled when ``password`` is empty; the
    ``model_post_init`` warning on the top-level Settings surfaces this.
    """

    model_config = SettingsConfigDict(env_prefix="COOKIECLOUD_", env_file_encoding="utf-8", extra="ignore")

    url: str = ""
    uuid: str = ""
    password: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.uuid and self.password)


class KugouMusicSettings(BaseSettings):
    """KuGou music sidecar settings (env prefix ``KUGOU_MUSIC_``).

    Music search/playback is unavailable when ``api_base_url`` is empty.
    """

    model_config = SettingsConfigDict(env_prefix="KUGOU_MUSIC_", env_file_encoding="utf-8", extra="ignore")

    api_base_url: str = ""
    cookie: str = ""


# --------------------------------------------------------------------------- #
# Top-level settings — flat fields without a clean group, plus grouped accessors.
# --------------------------------------------------------------------------- #


class Settings(BaseSettings):
    """Top-level application settings.

    Grouped config is accessed via the cached properties below
    (``settings.redis``, ``settings.postgres``, ...); flat fields that do not
    belong to a group live here directly.
    """

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    PORT: int = 8001
    THUMBNAILS_PATH: str = ""
    CLIP_MARKER_PREVIEWS_PATH: str = ""
    CLOUDFLARE_BYPASS_SERVICE_URL: str = ""
    JWT_SECRET_KEY: str = ""

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "JWT_SECRET_KEY must be set via environment variable or .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v

    CORS_ALLOW_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Crawl-related fields whose env-var names carry no CRAWL_ prefix.
    FULL_SYNC_MAX_INFLIGHT: int = 2
    FULL_SYNC_SITE_MAX_INFLIGHT: int = 1
    CHANNEL_UPDATE_DEFAULT_SIZE: int = 30

    # --- grouped accessors (each is a process-wide singleton) --- #

    @property
    def redis(self) -> RedisSettings:
        return _get_redis_settings()

    @property
    def postgres(self) -> PostgresSettings:
        return _get_postgres_settings()

    @property
    def meili(self) -> MeiliSettings:
        return _get_meili_settings()

    @property
    def crawl(self) -> CrawlSettings:
        return _get_crawl_settings()

    @property
    def mq(self) -> MqSettings:
        return _get_mq_settings()

    @property
    def cookiecloud(self) -> CookieCloudSettings:
        return _get_cookiecloud_settings()

    @property
    def kugou_music(self) -> KugouMusicSettings:
        return _get_kugou_music_settings()

    # --- environment / derived helpers --- #

    @property
    def environment(self) -> str:
        return _env()

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def database_url(self) -> str:
        return self.postgres.url

    @property
    def config_dir(self) -> Path:
        return base_dir.parent / "config"

    @property
    def base_dir(self) -> Path:
        """Backend project root directory."""
        return base_dir

    @property
    def static_dir(self) -> Path:
        """Backend static files directory (backend/static)."""
        return self.base_dir / "static"

    @property
    def thumbnails_dir(self) -> Path:
        """Directory for cached video thumbnails (backend/static/thumbnails)."""
        if self.THUMBNAILS_PATH:
            return Path(self.THUMBNAILS_PATH)
        return self.static_dir / "thumbnails"

    @property
    def clip_marker_previews_dir(self) -> Path:
        """Directory for persisted clip marker preview images."""
        if self.CLIP_MARKER_PREVIEWS_PATH:
            return Path(self.CLIP_MARKER_PREVIEWS_PATH)
        return self.static_dir / "clip-markers"

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    def optional_feature_warnings(self) -> list[str]:
        """Human-readable notices for optional features that are disabled due to missing config.

        Pure query (no side effects): startup entrypoints (lifespan / worker
        bootstrap) call this and decide how to log them. Keeping the notices
        out of construction avoids log spam during tests, alembic, and scripts.
        """
        warnings: list[str] = []
        if not self.cookiecloud.is_configured:
            warnings.append(
                "COOKIECLOUD not configured (set COOKIECLOUD_URL/UUID/PASSWORD) "
                "— CookieCloud sync unavailable"
            )
        if not self.kugou_music.api_base_url:
            warnings.append(
                "KUGOU_MUSIC_API_BASE_URL not set — Kugou music search/playback unavailable"
            )
        return warnings


# --------------------------------------------------------------------------- #
# Singleton resolution for each sub-settings group.
# --------------------------------------------------------------------------- #


@lru_cache
def _get_redis_settings() -> RedisSettings:
    return RedisSettings()


@lru_cache
def _get_postgres_settings() -> PostgresSettings:
    return PostgresSettings()


@lru_cache
def _get_meili_settings() -> MeiliSettings:
    return MeiliSettings()


@lru_cache
def _get_crawl_settings() -> CrawlSettings:
    return CrawlSettings()


@lru_cache
def _get_mq_settings() -> MqSettings:
    return MqSettings()


@lru_cache
def _get_cookiecloud_settings() -> CookieCloudSettings:
    return CookieCloudSettings()


@lru_cache
def _get_kugou_music_settings() -> KugouMusicSettings:
    return KugouMusicSettings()


def reset_sub_settings_cache() -> None:
    """Clear all sub-settings caches (test-only; allows env switching between cases)."""
    _get_redis_settings.cache_clear()
    _get_postgres_settings.cache_clear()
    _get_meili_settings.cache_clear()
    _get_crawl_settings.cache_clear()
    _get_mq_settings.cache_clear()
    _get_cookiecloud_settings.cache_clear()
    _get_kugou_music_settings.cache_clear()


# --------------------------------------------------------------------------- #
# Lazy-loading machinery (PEP 562 module __getattr__).
#
# Importing this module no longer eagerly constructs the Settings singleton —
# env is only read on the first attribute access (``settings.X``). This removes
# the import-time side effect while keeping every ``from ... import settings``
# site unchanged: the ``settings`` name is resolved lazily via __getattr__.
# --------------------------------------------------------------------------- #

_settings_instance: Settings | None = None


@lru_cache
def _resolve_env_file() -> Path:
    """Resolve the .env file path from the ENV variable (e.g. .env.dev)."""
    env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
    return base_dir.parent / env_file


def get_settings() -> Settings:
    """Return the process-wide Settings singleton, constructing it on first use."""
    global _settings_instance
    if _settings_instance is None:
        load_dotenv(_resolve_env_file(), override=True)
        _settings_instance = Settings()
    return _settings_instance


def _reset_settings_cache() -> None:
    """Clear the cached singleton (test-only; allows env switching between cases)."""
    global _settings_instance
    _settings_instance = None
    reset_sub_settings_cache()


def __getattr__(name: str) -> Any:
    """Module-level lazy proxy.

    ``from infrastructure.config.settings import settings`` resolves ``settings``
    through this hook on first access, deferring env parsing until actually used.
    """
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
