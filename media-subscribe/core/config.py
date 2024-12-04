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
    MYSQL_HOST: str = 'localhost'
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = 'root'
    MYSQL_PASSWORD: str = 'root'
    MYSQL_DATABASE: str = 'media_subscribe'
    MEDIA_DOWNLOAD_PATH: str = str(Path(os.path.join(base_dir, '..', 'downloads')))
    COOKIE_TYPE: str = 'file'
    COOKIE_CLOUD_URL: str = ''
    COOKIE_CLOUD_UUID: str = ''
    COOKIE_CLOUD_PASSWORD: str = ''
    COOKIE_CLOUD_DOMAIN: str = ''

    POOL_SIZE: int = 30
    POOL_MAX_SIZE: int = 60
    POOL_RECYCLE: int = 300
    CHANNEL_UPDATE_DEFAULT_SIZE: int = 10
    DOWNLOAD_RETRY_THRESHOLD: int = 5
    DOWNLOAD_CONSUMERS: int = 1
    EXTRACT_CONSUMERS: int = 2
    SUBSCRIBE_CONSUMERS: int = 1

    class Config:
        env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self):
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    def get_download_root_path(self):
        download_path = Path(os.path.join(base_dir, '..', 'downloads'))
        return os.getenv('MEDIA_DOWNLOAD_PATH', download_path)

    def get_cookies_file_path(self):
        cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies.txt'))
        return os.path.normpath(cookie_path)

    def get_cookies_file_path_thread(self, queue_thread_name: str):
        queue_thread_name = queue_thread_name.replace(':', '-')
        cookie_path = Path(os.path.join(base_dir, '..', 'config', f'cookies-{queue_thread_name}.txt'))
        with open(cookie_path, 'w') as wf:
            with open(self.get_cookies_file_path(), 'r') as rf:
                wf.write(rf.read())
        return os.path.normpath(cookie_path)

    def get_cookies_http_file_path(self):
        http_cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies_http.txt'))
        return os.path.normpath(http_cookie_path)

    def get_redis_url(self):
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings():
    env_file = f".env.{os.getenv('ENV')}" if os.getenv("ENV") else ".env"
    env_path = os.path.join(os.path.dirname(base_dir), env_file)
    load_dotenv(env_path, override=True)
    return Settings()


settings = get_settings()
