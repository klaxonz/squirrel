from datetime import datetime
from peewee import *
from model.base import BaseModel


class Channel(BaseModel):
    id = AutoField()
    channel_id = CharField(max_length=255)
    name = CharField(max_length=255)
    url = CharField(max_length=1024)
    if_enable = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    @staticmethod
    def subscribe(channel_id, name, url):
        # 查看是否已经订阅了 channel
        channel = Channel.select().where(Channel.url == url).first()
        if channel:
            return channel

        Channel.insert(
            channel_id=channel_id,
            name=name,
            url=url,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ).execute()

    @staticmethod
    def unsubscribe(id):
        Channel.update(
            if_enable=False,
            updated_at=datetime.now()
        ).where(Channel.id == id).execute()
