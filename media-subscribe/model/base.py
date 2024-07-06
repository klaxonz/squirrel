from peewee import Model

from common.database import ReconnectPooledMySQLDatabase


def make_table_name(model_class):
    model_name = model_class.__name__
    return ''.join(['_' + c.lower() if c.isupper() else c for c in model_name]).lstrip('_')


class BaseModel(Model):
    class Meta:
        table_function = make_table_name
        database = ReconnectPooledMySQLDatabase.get_db_instance()
