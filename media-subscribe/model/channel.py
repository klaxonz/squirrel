from datetime import datetime
from peewee import *
from ..common.database import DbInstanceHolder


class Channel(Model):
    id = IntegerField(primary_key=True, and_auto_increment=True)
    name = CharField(max_length=255)
    url = CharField(max_length=255)
    if_enable = BooleanField(default=True)
    website = CharField(max_length=255)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = DbInstanceHolder.get_instance()

    def subscribe(self, name, url):
        # 查看是否已经订阅了 channel
        channel = Channel.select().where(Channel.url == url).get()
        if channel:
            return channel

        Channel.insert(
            name=name,
            url=url,
            website=self.website,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ).execute()

    def unsubscribe(self, id):
        Channel.update(
            if_enable=False,
            updated_at=datetime.now()
        ).where(Channel.id == id).execute()
