import threading

from playhouse.db_url import connect
from common.config import GlobalConfig
import logging
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)


class DatabaseManager:
    @classmethod
    def create_database_if_not_exists(cls, database_name, connection):
        cursor = connection.cursor()
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name};")
            logger.info(f"Database '{database_name}' created successfully.")
        except Error as e:
            logger.error(f"Error occurred: ", e)

    @classmethod
    def establish_connection(cls):
        try:
            connection = mysql.connector.connect(
                host=GlobalConfig.get_mysql_host(),
                port=GlobalConfig.get_mysql_port(),
                user=GlobalConfig.get_mysql_user(),
                password=GlobalConfig.get_mysql_password()
            )
            return connection
        except Error as e:
            logger.error(f"Error while connecting to MySQL", e)
            return None

    @classmethod
    def initialize_database(cls, tables):
        connection = cls.establish_connection()
        if connection is not None:
            cls.create_database_if_not_exists(GlobalConfig.DEFAULT_MYSQL_DATABASE, connection)
        db = DbInstanceHolder.get_instance()
        db.create_tables(tables)


class DbInstanceHolder:
    _lock = threading.Lock()
    _instance = None

    def __new__(cls):
        """确保DbInstanceHolder是单例，且线程安全"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DbInstanceHolder, cls).__new__(cls)
                cls._instance.db_instance = connect(url=GlobalConfig.get_mysql_url())
        return cls._instance

    @classmethod
    def get_instance(cls):
        """获取DbInstanceHolder的单例实例"""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance.db_instance
