# Queue processors using the new queue management system
#
# 显式导入所有 processor 模块以确保：
# 1. 装饰器注册的消费者被加载
# 2. 动态注册函数（_register_domain_consumers）被执行
from . import extract_task
from . import update_subscription_task
from . import download_task
from . import subscribe_task

__all__ = [
    'extract_task',
    'update_subscription_task',
    'download_task',
    'subscribe_task',
]
