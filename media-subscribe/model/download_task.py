from datetime import datetime

from peewee import (
    AutoField,
    BigIntegerField,
    CharField,
    IntegerField,
    DateTimeField,
)

from model.base import BaseModel


class DownloadTask(BaseModel):
    """
    下载任务表的Peewee Model定义
    """
    task_id = AutoField(primary_key=True, verbose_name='任务ID')
    url = CharField(max_length=2048, null=False, verbose_name='下载链接')
    domain = CharField(max_length=255, null=False, verbose_name='下载链接域名')
    video_id = CharField(max_length=64, null=False, verbose_name='视频ID')
    title = CharField(max_length=255, null=True, verbose_name='视频标题')
    status = CharField(choices=['PENDING', 'DOWNLOADING', 'COMPLETED', 'FAILED', 'CANCELLED'], null=False,
                       default='PENDING', verbose_name='任务状态')
    downloaded_size = BigIntegerField(null=False, default=0, verbose_name='已下载大小（字节）')
    total_size = BigIntegerField(null=True, verbose_name='总大小（字节）')
    speed = IntegerField(null=True, verbose_name='下载速度（字节/秒）')
    eta = CharField(max_length=32, null=True, verbose_name='预计剩余下载时间')
    error_message = CharField(null=True, verbose_name='失败原因或错误信息')
    created_at = DateTimeField(null=False, default=datetime.now, verbose_name='创建时间')
    updated_at = DateTimeField(null=False, default=datetime.now, verbose_name='更新时间')

    def __str__(self):
        return f'Task ID: {self.task_id}, Title: {self.title}, Status: {self.status}'

