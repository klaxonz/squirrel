import threading

import mysql
from mysql.connector import Error
from peewee import OperationalError
from playhouse.pool import PooledMySQLDatabase, MaxConnectionsExceeded
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

    reconnect_errors = (
        # Error class, error message fragment (or empty string for all).
        (OperationalError, '2006'),  # MySQL server has gone away.
        (OperationalError, '2013'),  # Lost connection to MySQL server.
        (OperationalError, '2014'),  # Commands out of sync.
        (OperationalError, '4031'),  # Client interaction timeout.

        # mysql-connector raises a slightly different error when an idle
        # connection is terminated by the server. This is equivalent to 2013.
        (OperationalError, 'MySQL Connection not available.'),
        (MaxConnectionsExceeded, 'Max connections exceeded, timed out attempting to connect.'),

        # Postgres error examples:
        # (OperationalError, 'terminat'),
        # (InterfaceError, 'connection already closed'),
    )

    _instance_lock = threading.Lock()
    _instance = None

    @classmethod
    def get_db_instance(cls):
        """Returns the singleton instance of the database connection pool."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(**db_config, max_connections=10, timeout=60, stale_timeout=60)
        return cls._instance

    def _reconnect(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # If we are in a transaction, do not reconnect silently as
            # any changes could be lost.
            if self.in_transaction():
                raise exc

            exc_class = type(exc)
            if exc_class not in self._reconnect_errors:
                raise exc

            exc_repr = str(exc).lower()
            for err_fragment in self._reconnect_errors[exc_class]:
                if err_fragment in exc_repr:
                    break
            else:
                raise exc

            if not self.is_closed():
                self.close()
                self.connect()
            else:
                self.connect()

            return func(*args, **kwargs)


class DatabaseManager:
    """Manages database initialization and table creation."""

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
        """Initializes the default database and creates tables if they don't exist."""
        # Assuming the default database is already created or will be created by another process.
        connection = cls.establish_connection()
        if connection is not None:
            cls.create_database_if_not_exists(GlobalConfig.DEFAULT_MYSQL_DATABASE, connection)
        db = ReconnectPooledMySQLDatabase.get_db_instance()
        with db:
            db.create_tables(tables, safe=True)  # Using 'safe=True' to avoid recreating existing tables
        logger.info("Database initialized successfully.")
