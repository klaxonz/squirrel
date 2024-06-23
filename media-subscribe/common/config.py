import os
from pathlib import Path

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GlobalConfig:
    DEFAULT_REDIS_HOST = 'localhost'
    DEFAULT_REDIS_PORT = 6379
    DEFAULT_MYSQL_HOST = 'localhost'
    DEFAULT_MYSQL_PORT = 3306
    DEFAULT_MYSQL_USER = 'root'
    DEFAULT_MYSQL_PASSWORD = 'root'
    DEFAULT_MYSQL_DATABASE = 'media_subscribe'
    CHANNEL_UPDATE_DEFAULT_SIZE = 10
    CHANNEL_UPDATE_ALL = False

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

    @classmethod
    def get_mysql_host(cls):
        return os.getenv('MYSQL_HOST', cls.DEFAULT_MYSQL_HOST)

    @classmethod
    def get_mysql_port(cls):
        return os.getenv('MYSQL_PORT', cls.DEFAULT_MYSQL_PORT)

    @classmethod
    def get_mysql_user(cls):
        return os.getenv('MYSQL_USER', cls.DEFAULT_MYSQL_USER)

    @classmethod
    def get_mysql_password(cls):
        return os.getenv('MYSQL_PASSWORD', cls.DEFAULT_MYSQL_PASSWORD)

    @classmethod
    def get_mysql_database(cls):
        return os.getenv('MYSQL_DATABASE', cls.DEFAULT_MYSQL_DATABASE)

    @classmethod
    def get_mysql_url(cls):
        host = cls.get_mysql_host()
        port = cls.get_mysql_port()
        user = cls.get_mysql_user()
        password = cls.get_mysql_password()
        database = cls.get_mysql_database()

        return f'mysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4'
