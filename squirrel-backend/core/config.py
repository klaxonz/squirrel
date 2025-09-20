import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # 保留原有的设置
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ''
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str = 'postgres'
    POSTGRES_DATABASE: str = 'squirrel'
    MEDIA_DOWNLOAD_PATH: str = str(Path(os.path.join(base_dir, '..', 'downloads')))
    COOKIE_TYPE: str = 'file'
    COOKIE_CLOUD_URL: str = ''
    COOKIE_CLOUD_UUID: str = ''
    COOKIE_CLOUD_PASSWORD: str = ''
    COOKIE_CLOUD_DOMAIN: str = ''

    POOL_SIZE: int = 30
    POOL_MAX_SIZE: int = 60
    POOL_RECYCLE: int = 300
    CHANNEL_UPDATE_DEFAULT_SIZE: int = 30

    class Config:
        env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"

    def get_redis_url(self):
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


def get_cookies_file_path():
    cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies.txt'))
    return os.path.normpath(cookie_path)


def get_cookies_file_path_thread(queue_thread_name: str):
    if not queue_thread_name:
        return get_cookies_file_path()
    queue_thread_name = queue_thread_name.replace(':', '-')
    cookie_path = Path(os.path.join(base_dir, '..', 'config', f'cookies-{queue_thread_name}.txt'))
    with open(cookie_path, 'w') as wf:
        with open(get_cookies_file_path(), 'r') as rf:
            wf.write(rf.read())
    return os.path.normpath(cookie_path)


def get_cookies_http_file_path():
    http_cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies_http.txt'))
    return os.path.normpath(http_cookie_path)


@lru_cache()
def get_settings():
    env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
    env_path = os.path.join(os.path.dirname(base_dir), env_file)
    load_dotenv(env_path, override=True)
    return Settings()


settings = get_settings()
