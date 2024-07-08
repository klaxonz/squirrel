import json
import time
from datetime import datetime, timedelta

from common.config import GlobalConfig
from common.database import get_session
from model.download_task import DownloadTask, DownloadTaskSchema
from model.channel import Channel
from common.message_queue import RedisMessageQueue, Message
from common.constants import QUEUE_EXTRACT_TASK
from threading import Thread
import logging

from service.download_service import start_extract, start_extract_and_download
from subscribe.subscribe import SubscribeChannelFactory

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

        interval *= 60 if unit == 'minutes' else 1  # 转换为秒

        if start_immediately:
            func()  # 立即执行一次

        # 计算第一次执行的时间
        next_run = time.time() + interval if start_immediately else time.time()

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
    def run(cls):
        try:
            # 执行查询
            ten_minutes_ago = datetime.now() - timedelta(minutes=5)
            with get_session() as session:
                tasks = session.query(DownloadTask).filter(
                    (DownloadTask.status == 'FAILED') | (DownloadTask.status.in_(('FAILED', 'PENDING', 'RUNNING', 'WAITING'))) &
                    (DownloadTask.updated_at <= ten_minutes_ago)
                ).all()
                # 把失败的任务放入redis队列,并修改状态
                for task in tasks:
                    message = Message()
                    message.body = DownloadTaskSchema().dumps(task)
                    session.add(message)
                    session.commit()

                    session.query(DownloadTask).filter(DownloadTask.task_id == task.task_id).update({
                        'status': 'PENDING'
                    })
                    session.commit()
                    RedisMessageQueue(QUEUE_EXTRACT_TASK).enqueue(message)

                    session.query(Message).filter(Message.message_id == message.message_id,
                                                  Message.send_status == 'PENDING').update({
                        'send_status': 'SENDING'
                    })
                    session.commit()
        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


class AutoUpdateChannelVideoTask:

    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                channels = session.query(Channel).filter(Channel.if_enable == 1).all()
                for channel in channels:
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
                    # 下载全部的
                    update_all = channel.if_download_all or channel.if_extract_all
                    video_list = subscribe_channel.get_channel_videos(channel=channel, update_all=update_all)
                    extract_video_list = []
                    extract_download_video_list = []
                    if channel.if_extract_all:
                        if channel.if_download_all:
                            extract_download_video_list = video_list
                        else:
                            if channel.if_auto_download:
                                extract_download_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
                            else:
                                extract_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
                    else:
                        if channel.if_auto_download:
                            extract_download_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
                        else:
                            extract_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]

                    for video in extract_video_list:
                        start_extract(video, channel)
                    for video in extract_download_video_list:
                        start_extract_and_download(video, channel)

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
