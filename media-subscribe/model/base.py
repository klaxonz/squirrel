from peewee import Model

from common.database import DbInstanceHolder


class BaseModel(Model):
    class Meta:
        database = DbInstanceHolder.get_instance()
