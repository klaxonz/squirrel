import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Backend project root directory (module-level for convenience)
base_dir = Path(__file__).parent.parent


class Settings(BaseSettings):

    model_config = {
        "env_file": f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ''
    REDIS_MAX_CONNECTIONS: int = 256
    REDIS_POOL_TIMEOUT: int = 10
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str = 'postgres'
    POSTGRES_DATABASE: str = 'squirrel'
    THUMBNAILS_PATH: str = ''
    CLOUDFLARE_BYPASS_SERVICE_URL: str = ''
    COOKIECLOUD_URL: str = ''
    COOKIECLOUD_UUID: str = ''
    COOKIECLOUD_PASSWORD: str = ''
    SQUIRREL_YOUTUBE_POT_PROVIDER_MODE: str = 'auto'
    SQUIRREL_YOUTUBE_POT_PROVIDER_BASE_URL: str = ''
    SQUIRREL_YOUTUBE_POT_PROVIDER_SERVER_HOME: str = ''

    POOL_SIZE: int = 30
    POOL_MAX_SIZE: int = 60
    POOL_RECYCLE: int = 300
    CHANNEL_UPDATE_DEFAULT_SIZE: int = 30

    MQ_CONSUMER_DEFAULT_COUNT: int = 1
    MQ_CONSUMER_COUNT_OVERRIDES: str = ''
    CRAWL_DEFAULT_SITE_CONCURRENCY: int = 2
    CRAWL_SITE_CONCURRENCY_OVERRIDES: str = ''
    CRAWL_TASK_TYPE_LIMITS: str = 'subscription_sync_incremental=2,subscription_sync_full=1,video_extract=8'
    CRAWL_SLOTS_PER_PROCESS: int = 8
    CRAWL_WORKER_LEASE_SECONDS: int = 60
    CRAWL_WORKER_POLL_INTERVAL_MS: int = 1000
    OUTBOX_NOTIFY_CHANNEL: str = 'outbox_events'
    OUTBOX_NOTIFY_POLL_TIMEOUT_SECONDS: int = 5
    OUTBOX_CONSUME_BATCH_SIZE: int = 50
    FULL_SYNC_MAX_INFLIGHT: int = 2
    FULL_SYNC_SITE_MAX_INFLIGHT: int = 1
    FULL_BACKFILL_RETRY_SECONDS: int = 300

    @property
    def environment(self) -> str:
        return os.getenv("ENV", "prod").lower()

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def config_dir(self) -> Path:
        return base_dir.parent / 'config'

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


@lru_cache()
def get_settings() -> Settings:
    env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
    env_path = base_dir.parent / env_file
    load_dotenv(env_path, override=True)
    return Settings()


settings = get_settings()
