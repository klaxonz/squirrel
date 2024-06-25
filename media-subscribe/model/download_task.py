import datetime
import json

from peewee import (
    AutoField,
    BigIntegerField,
    CharField,
    IntegerField,
    TimestampField,
)

from model.base import BaseModel


class DownloadStatusEnum(CharField):
    """自定义EnumField类型，映射数据库中的ENUM类型"""
    choices = ['PENDING', 'DOWNLOADING', 'COMPLETED', 'FAILED', 'CANCELLED']


class DownloadTask(BaseModel):
    """
    下载任务表的Peewee Model定义
    """
    task_id = AutoField(primary_key=True, verbose_name='任务ID')
    url = CharField(max_length=2048, null=False, verbose_name='下载链接')
    domain = CharField(max_length=255, null=False, verbose_name='下载链接域名')
    video_id = CharField(max_length=64, null=False, verbose_name='视频ID')
    title = CharField(max_length=255, null=True, verbose_name='视频标题')
    status = DownloadStatusEnum(null=False, default='PENDING', verbose_name='任务状态')
    downloaded_size = BigIntegerField(null=False, default=0, verbose_name='已下载大小（字节）')
    total_size = BigIntegerField(null=True, verbose_name='总大小（字节）')
    speed = IntegerField(null=True, verbose_name='下载速度（字节/秒）')
    eta = CharField(max_length=32, null=True, verbose_name='预计剩余下载时间')
    error_message = CharField(null=True, verbose_name='失败原因或错误信息')
    created_at = TimestampField(null=False, default=datetime.datetime.now, verbose_name='创建时间')
    updated_at = TimestampField(null=False, default=datetime.datetime.now, verbose_name='更新时间')

    def __str__(self):
        return f'Task ID: {self.task_id}, Title: {self.title}, Status: {self.status}'

    def to_dict(self):
        """
        将DownloadTask实例转换为字典。
        """
        data = {
            'task_id': self.task_id,
            'url': self.url,
            'domain': self.domain,
            'video_id': self.video_id,
            'title': self.title,
            'status': self.status.value,  # 获取Enum的值
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.speed,
            'eta': self.eta,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),  # 转换为ISO 8601格式字符串
            'updated_at': self.updated_at.isoformat(),
        }
        return data

    def to_json(self):
        """
        将DownloadTask实例转换为JSON字符串。
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)


def json_to_downloadtask(json_data) -> DownloadTask:
    """
    从JSON数据创建或更新DownloadTask实例。
    """
    # 解析JSON数据
    data = json.loads(json_data)

    # 特殊处理：将字符串格式的日期时间转换回datetime对象
    data['created_at'] = datetime.fromisoformat(data['created_at'])
    data['updated_at'] = datetime.fromisoformat(data['updated_at'])

    # 特殊处理：将枚举值转换为DownloadStatusEnum实例
    data['status'] = DownloadStatusEnum(data['status'])

    # 根据情况创建或更新DownloadTask实例
    # 这里简化处理，直接尝试创建新实例，具体逻辑可能需要根据业务调整
    download_task, _ = DownloadTask.get_or_create(
        defaults=data,
        task_id=data['task_id']
    )

    return download_task
