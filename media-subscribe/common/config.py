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
    POOL_SIZE = 10
    POOL_MAX_SIZE = 60
    POOL_RECYCLE = 300
    CHANNEL_UPDATE_DEFAULT_SIZE = 10
    DOWNLOAD_RETRY_THRESHOLD = 5

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
        return os.path.normpath(cookie_path)

    @classmethod
    def get_cookies_file_path_thread(cls, queue_thread_name: str):
        """
        获取cookie文件路径
        """
        queue_thread_name = queue_thread_name.replace(':', '-')
        cookie_path = Path(os.path.join(base_dir, '..', 'config', f'cookies-{queue_thread_name}.txt'))
        with open(cookie_path, 'w') as wf:
            with open(cls.get_cookies_file_path(), 'r') as rf:
                wf.write(rf.read())
        return os.path.normpath(cookie_path)


    @classmethod
    def get_cookies_http_file_path(cls):
        """
        获取cookie文件路径
        """
        http_cookie_path = Path(os.path.join(base_dir, '..', 'config', 'cookies_http.txt'))
        return os.path.normpath(http_cookie_path)

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
        """Get MySQL port from environment variable or return default."""
        port = os.getenv('MYSQL_PORT')
        return int(port) if port is not None else cls.DEFAULT_MYSQL_PORT

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

        return f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4'

    @classmethod
    def get_cookie_type(cls):
        """
        获取cookie类型
        """
        return os.getenv('COOKIE_TYPE', 'file')

    @classmethod
    def get_cookie_cloud_url(cls):
        """
        获取cookie云地址
        """
        return os.getenv('COOKIE_CLOUD_URL', '')

    @classmethod
    def get_cookie_cloud_uuid(cls):
        """
        获取cookie云uuid
        """
        return os.getenv('COOKIE_CLOUD_UUID', '')

    @classmethod
    def get_cookie_cloud_password(cls):
        """
        获取cookie云密码
        """
        return os.getenv('COOKIE_CLOUD_PASSWORD', '')

    @classmethod
    def get_cookie_cloud_domain(cls):
        """
        获取cookie云类型
        """
        return os.getenv('COOKIE_CLOUD_DOMAIN', '')
