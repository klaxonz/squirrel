import datetime
import json

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

    def to_dict(self):
        data = {
            'message_id': self.message_id,
            'body': self.body,
            'send_status': self.send_status.value,
            'retry_count': self.retry_count,
            'next_retry_time': self.next_retry_time.isoformat() if self.next_retry_time else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        return data

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)


def json_to_message(json_data):
    """
    从JSON数据创建或更新Message实例。
    """
    # 解析JSON数据
    data = json.loads(json_data)

    # 特殊处理：将字符串格式的日期时间转换回datetime对象
    if 'next_retry_time' in data and data['next_retry_time']:
        data['next_retry_time'] = datetime.fromisoformat(data['next_retry_time'].replace("Z", "+00:00"))  # 处理ISO 8601格式
    if 'created_at' in data:
        data['created_at'] = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
    if 'updated_at' in data:
        data['updated_at'] = datetime.strptime(data['updated_at'], '%Y-%m-%d %H:%M:%S')

    # 特殊处理：将枚举值转换为SendStatusEnum实例
    data['send_status'] = SendStatusEnum(data['send_status'])

    # 创建或更新Message实例
    # 注意：这里的逻辑取决于你的具体需求，例如是否需要先查找数据库中是否存在相同message_id的记录
    message_instance, created = Message.get_or_create(
        defaults=data,
        message_id=data['message_id']
    )

    return message_instance
