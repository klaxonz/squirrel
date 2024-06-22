import os
from pathlib import Path

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GlobalConfig:
    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379

    @classmethod
    def get_download_root_path(cls):
        """
        获取下载根目录
        """
        download_path = Path(os.path.join(base_dir, '..', 'downloads'))
        return os.getenv('MEDIA_DOWNLOAD_PATH', download_path)

    @classmethod
    def get_cookies_file_path(cls):
        """
        获取cookie文件路径
        """
        cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies.txt'))
        if cookie_path.exists():
            return str(cookie_path)
        else:
            return None

    @classmethod
    def get_redis_host(cls):
        return os.getenv('REDIS_HOST', cls.DEFAULT_REDIS_HOST)

    @classmethod
    def get_redis_port(cls):

        return os.getenv('REDIS_PORT', cls.DEFAULT_REDIS_PORT)
