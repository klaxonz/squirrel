import logging
import time
from threading import Thread

logger = logging.getLogger()


class Scheduler:
    def __init__(self):
        self.jobs = []
        self.running = False

    def _run_jobs(self):
        """内部方法，循环检查并执行到期的任务"""
        while self.running:
            current_time = time.time()
            for job in self.jobs[:]:
                if job['next_run'] <= current_time:
                    thread = Thread(target=job['func'])
                    thread.start()
                    job['next_run'] += job['interval']
            time.sleep(1)

    def add_job(self, func, interval, unit='seconds', start_immediately=True):
        """
        添加一个定时任务。
        
        :param func: 要执行的函数
        :param interval: 执行间隔
        :param unit: 时间间隔单位，默认为秒
        :param start_immediately: 是否立即执行一次，默认为True
        """
        if unit not in ['seconds', 'minutes']:
            raise ValueError("unit must be 'seconds' or 'minutes'")

        interval *= 60 if unit == 'minutes' else 1
        next_run = time.time() if start_immediately else time.time() + interval

        self.jobs.append({
            'func': func,
            'interval': interval,
            'next_run': next_run,
        })

    def start(self):
        """启动调度器"""
        if not self.running:
            self.running = True
            thread = Thread(target=self._run_jobs)
            thread.daemon = True
            thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False
