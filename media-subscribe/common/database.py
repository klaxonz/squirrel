from peewee import SqliteDatabase
import os

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
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_file = os.path.join(base_dir, '..', 'db', 'db.sqlite')
        if not os.path.exists(db_file):
            with open(db_file, 'w'):
                pass

        self.db_instance = SqliteDatabase(db_file)
        self.db_instance.connect()

    @classmethod
    def get_instance(cls):
        """获取DbInstanceHolder的单例实例"""
        if cls._instance is None:
            cls._instance = DbInstanceHolder()
        elif cls._instance.db_instance.is_closed():
            cls._instance.db_instance.connect()
        return cls._instance.db_instance
