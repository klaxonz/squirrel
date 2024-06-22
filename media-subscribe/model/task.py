import json
from datetime import datetime
from peewee import *
from ..common.database import DbInstanceHolder
from ..common.message_queue import RedisMessageQueue, Message

class Task(Model):
    STATUS_NOT_STARTED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_COMPLETED = 2
    STATUS_FAILED = 3
    
    id = CharField(primary_key=True)
    task_type = CharField()
    message = CharField()
    status = IntegerField(default=STATUS_NOT_STARTED)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField()

    class Meta:
        database = DbInstanceHolder.get_instance()
        
        
    @classmethod
    def create_task(cls, task_id, message):
        """创建新的下载任务，根据message类型处理存储逻辑"""
        if isinstance(message, Message):
            message_content = json.dumps(message.to_dict())
        else:
            message_content = message
        
        return cls.create(
            id=task_id,
            type=message.type,
            message=message_content,
            updated_at=datetime.now())

    @classmethod
    def get_task(cls, task_id):
        """根据ID获取任务详情"""
        return cls.get_or_none(cls.id == task_id)

    @classmethod
    def update_status(cls, task_id, new_status):
        """更新任务状态"""
        timestamp = datetime.now()
        cls.update(
            status=new_status,
            updated_at=timestamp,
        ).where(cls.id == task_id).execute()

    @classmethod
    def mark_as_in_not_start(cls, task_id):
        """标记任务为下载中"""
        cls.update_status(task_id, cls.STATUS_NOT_STARTED)

    @classmethod
    def mark_as_in_progress(cls, task_id):
        """标记任务为下载中"""
        cls.update_status(task_id, cls.STATUS_IN_PROGRESS)

    @classmethod
    def mark_as_completed(cls, task_id):
        """标记任务为下载完成"""
        cls.update_status(task_id, cls.STATUS_COMPLETED)

    @classmethod
    def mark_as_failed(cls, task_id):
        """标记任务为下载失败，并附带错误信息"""
        cls.update_status(task_id, cls.STATUS_FAILED)

    @classmethod
    def list_tasks(cls, status=None, order_by='created_at', order='asc'):
        """
        列出所有任务，可选参数status过滤状态，并按指定字段和顺序排序。
        
        :param status: 可选，筛选任务状态，默认为None，即不过滤状态。
        :param order_by: 排序依据字段，默认为'created_at'，可选'updated_at'。
        :param order: 排序方式，默认为'asc'（升序），可选'desc'（降序）。
        """
        query = cls.select()
        
        # 状态过滤
        if status is not None:
            query = query.where(cls.status == status)
        
        # 添加排序
        if order_by == 'created_at':
            sort_field = cls.created_at
        elif order_by == 'updated_at':
            sort_field = cls.updated_at
        else:
            raise ValueError("Invalid order_by field. Supported fields are 'created_at' and 'updated_at'.")
        
        if order == 'desc':
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        return list(query.execute())
    
