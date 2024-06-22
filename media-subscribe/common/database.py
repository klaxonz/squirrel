from peewee import *
from peewee import SqliteDatabase

class DatabaseManager:

    @classmethod
    def initialize_database(cls, tables):
        db = DbInstanceHolder.get_instance()
        db.create_tables(tables, safe=True)
        db.close()


class DbInstanceHolder:
    _instance = None

    def __init__(self):
        if DbInstanceHolder._instance is not None:
            raise Exception("DbInstanceHolder is a singleton. Use get_instance() instead.")
        self.db_instance = SqliteDatabase("db/db.sqlite")
        self.db_instance.connect()

    @classmethod
    def get_instance(cls):
        """获取DbInstanceHolder的单例实例"""
        if cls._instance is None:
            cls._instance = DbInstanceHolder()
        elif cls._instance.db_instance.is_closed():
            cls._instance.db_instance.connect()
        return cls._instance.db_instance