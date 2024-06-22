import json
import time
from model.task import Task
from common.message_queue import RedisMessageQueue, Message
from common.constants import QUEUE_DOWNLOAD_TASK
from threading import Thread
import logging

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.jobs = []
        self.running = False

    def _run_jobs(self):
        """内部方法，循环检查并执行到期的任务"""
        while self.running:
            current_time = time.time()
            for job in self.jobs[:]:  # 复制列表以允许在循环中安全移除元素
                if job['next_run'] <= current_time:
                    job['func']()
                    # 重新计算下次运行时间，这里简单地按固定间隔计算
                    job['next_run'] += job['interval']
            # 避免高CPU占用，休眠一段时间再检查
            time.sleep(1)

    def add_job(self, func, interval, unit='seconds', startImmediately=True):
        """
        添加一个定时任务。
        
        :param func: 要执行的函数
        :param interval: 执行间隔
        :param unit: 时间间隔单位，默认为秒
        :param startImmediately: 是否立即执行一次，默认为True
        """
        if unit not in ['seconds', 'minutes']:
            raise ValueError("unit must be 'seconds' or 'minutes'")

        interval *= 60 if unit == 'minutes' else 1  # 转换为秒

        if startImmediately:
            func()  # 立即执行一次

        # 计算第一次执行的时间
        next_run = time.time() + interval if startImmediately else time.time()

        self.jobs.append({
            'func': func,
            'interval': interval,
            'next_run': next_run,
        })

        if not self.running:
            self.running = True
            thread = Thread(target=self._run_jobs)
            thread.daemon = True
            thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False


class RetryFailedTask:

    @classmethod
    def retry_failed_task(cls):
        try:
            # 查询 50 条失败的任务
            tasks = Task.list_tasks(Task.STATUS_FAILED)
            # 把失败的任务放入redis队列,并修改状态
            for task in tasks:
                # 注意：这里假设json.loads可能会因为task.message格式不正确而抛出异常
                message_content = json.loads(task.message)
                message = Message(content=message_content, message_id=task.id, type=task.task_type)
                RedisMessageQueue(QUEUE_DOWNLOAD_TASK).enqueue(message)
                Task.mark_as_in_not_start(task.id)
        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}")
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}")
