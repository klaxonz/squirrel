import threading

from peewee import SqliteDatabase
import os


class DatabaseManager:

    @classmethod
    def initialize_database(cls, tables):
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
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_file = os.path.join(base_dir, '..', 'db', 'db.sqlite')
                cls._instance.db_instance = SqliteDatabase(db_file,  pragmas={
                    'journal_mode': 'wal',
                    'cache_size': 10000,
                })
        return cls._instance

    @classmethod
    def get_instance(cls):
        """获取DbInstanceHolder的单例实例"""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance.db_instance
