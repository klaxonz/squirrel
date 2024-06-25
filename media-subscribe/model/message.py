import datetime
from model.base import BaseModel
from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    IntegerField,
    TimestampField,
    TextField
)


class SendStatusEnum(CharField):
    """自定义EnumField类型，映射数据库中的ENUM类型"""
    choices = ['PENDING', 'SENDING', 'SUCCESS', 'FAILURE']


class Message(BaseModel):
    """
    本地消息表的Peewee Model定义
    """
    message_id = AutoField(primary_key=True, verbose_name='消息ID')
    body = TextField(null=False, verbose_name='消息内容')
    send_status = SendStatusEnum(null=False, default='PENDING', verbose_name='发送状态')
    retry_count = IntegerField(null=False, default=0, verbose_name='重试次数')
    next_retry_time = DateTimeField(null=True, verbose_name='下次重试时间')
    created_at = TimestampField(null=False, default=datetime.datetime.now, verbose_name='创建时间')
    updated_at = TimestampField(null=False, default=datetime.datetime.now, verbose_name='更新时间')

    def __str__(self):
        return f'Message ID: {self.message_id}, Status: {self.send_status}'
