from datetime import datetime
from peewee import *
from model.base import BaseModel


class Channel(BaseModel):
    id = AutoField()
    channel_id = CharField(max_length=255)
    name = CharField(max_length=255)
    url = CharField(max_length=1024)
    if_enable = BooleanField(default=True)
    if_auto_download = BooleanField(default=False)
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


class ChannelVideo(BaseModel):
    id = AutoField()
    channel_id = CharField(max_length=255, null=False, verbose_name='频道ID')
    channel_name = CharField(max_length=255, null=False, verbose_name='频道名称')
    title = CharField(max_length=255, null=True, verbose_name='视频标题')
    video_id = CharField(max_length=64, null=False, verbose_name='视频ID')
    domain = CharField(max_length=255, null=False, verbose_name='视频链接域名')
    url = CharField(max_length=1024, null=False, verbose_name='视频链接')
    thumbnail = CharField(max_length=2048, null=True, verbose_name='视频封面链接')
    if_read = BooleanField(default=False, verbose_name='是否已读')
    if_downloaded = BooleanField(default=False, verbose_name='是否已下载')
    uploaded_at = DateTimeField(null=True, verbose_name='上传时间')
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

