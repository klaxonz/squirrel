import threading
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import ReconnectMixin
from common.config import GlobalConfig
import logging

logger = logging.getLogger(__name__)

db_config = {
    'host': GlobalConfig.get_mysql_host(),
    'port': GlobalConfig.get_mysql_port(),
    'user': GlobalConfig.get_mysql_user(),
    'password': GlobalConfig.get_mysql_password(),
    'database': GlobalConfig.get_mysql_database(),
}


class ReconnectPooledMySQLDatabase(ReconnectMixin, PooledMySQLDatabase):
    """Thread-safe singleton pattern for pooled MySQL database with reconnect capabilities."""

    _instance_lock = threading.Lock()
    _instance = None

    @classmethod
    def get_db_instance(cls):
        """Returns the singleton instance of the database connection pool."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(**db_config, max_connections=20)
        return cls._instance


class DatabaseManager:
    """Manages database initialization and table creation."""

    @classmethod
    def create_database_if_not_exists(cls, database_name):
        """Creates a database if it does not exist."""
        try:
            with ReconnectPooledMySQLDatabase.get_db_instance().connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name};")
                    logger.info(f"Database '{database_name}' created successfully.")
        except Exception as e:
            logger.error(f"Error creating database '{database_name}': {e}")

    @classmethod
    def initialize_database(cls, tables):
        """Initializes the default database and creates tables if they don't exist."""
        # Assuming the default database is already created or will be created by another process.
        db = ReconnectPooledMySQLDatabase.get_db_instance()
        with db:
            db.create_tables(tables, safe=True)  # Using 'safe=True' to avoid recreating existing tables
        logger.info("Database initialized successfully.")
