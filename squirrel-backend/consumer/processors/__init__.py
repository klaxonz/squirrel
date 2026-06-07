# Queue processors using the new queue management system
#
# 显式导入所有 processor 模块以确保：
# 1. 装饰器注册的消费者被加载
# 2. 订阅相关消费者被加载
from . import subscribe_task

__all__ = [
    "subscribe_task",
]
