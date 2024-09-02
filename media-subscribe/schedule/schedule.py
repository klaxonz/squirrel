import concurrent.futures
import json
import logging
import random
import time
from datetime import datetime, timedelta
from threading import Thread

from PyCookieCloud import PyCookieCloud
from sqlalchemy import text

from common.config import GlobalConfig
from common.cookie import json_cookie_to_netscape
from common.database import get_session
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from service.download_service import start
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
                    thread = Thread(target=job['func'])
                    thread.start()
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

        # 计算第一次执行的时间
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


class SyncCookies:

    @classmethod
    def run(cls):
        try:
            cookie_cloud = PyCookieCloud(GlobalConfig.get_cookie_cloud_url(), GlobalConfig.get_cookie_cloud_uuid(),
                                         GlobalConfig.get_cookie_cloud_password())
            the_key = cookie_cloud.get_the_key()
            if not the_key:
                logger.info('Failed to get the key')
                return
            encrypted_data = cookie_cloud.get_encrypted_data()
            if not encrypted_data:
                logger.info('Failed to get encrypted data')
                return
            decrypted_data = cookie_cloud.get_decrypted_data()
            if not decrypted_data:
                logger.info('Failed to get decrypted data')
                return
            domains = GlobalConfig.get_cookie_cloud_domain()
            if domains:
                expect_domains = domains.split(',')
            else:
                expect_domains = []

            json_cookie_to_netscape(decrypted_data, expect_domains, GlobalConfig.get_cookies_file_path())
            json_cookie_to_netscape(decrypted_data, expect_domains, GlobalConfig.get_cookies_http_file_path())

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


class RetryFailedTask:

    @classmethod
    def run(cls):
        try:
            # 执行查询
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            with get_session() as session:
                tasks = session.query(DownloadTask).filter(
                    text(
                        "(status = 'FAILED' and retry < 5) or (status in ('DOWNLOADING', 'PENDING', 'WAITING') and retry < 5 and updated_at < :update_time)")
                    .params(update_time=five_minutes_ago)
                )

                # 把失败的任务放入redis队列,并修改状态
                for task in tasks:
                    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                    downloading_tasks = session.query(DownloadTask).filter(
                        (DownloadTask.status == 'DOWNLOADING') &
                        (DownloadTask.updated_at <= ten_minutes_ago)
                    ).all()

                    if (task.status == 'PENDING' or task.status == 'WAITING') and len(downloading_tasks) > 0:
                        continue

                    task.error_message = ''
                    task.status = 'PENDING'
                    task.retry = task.retry + 1
                    session.commit()

                    channel = session.query(Channel).filter(Channel.channel_id == task.channel_id).first()
                    if_subscribe = channel is not None
                    start(task.url, if_only_extract=False, if_subscribe=if_subscribe, if_retry=True)

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


class ChangeStatusTask:

    @classmethod
    def run(cls):
        try:
            # 执行查询
            with get_session() as session:
                tasks = session.query(DownloadTask).filter(DownloadTask.status == 'PENDING', DownloadTask.retry >= 5)

                # 把失败的任务放入redis队列,并修改状态
                for task in tasks:
                    task.status = 'FAILED'
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
                    session.expunge(channel)

            # 使用线程池并行处理每个channel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                [executor.submit(cls.update_channel_video, channel) for channel in channels]

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def update_channel_video(cls, channel):
        logger.debug(f"update {channel.name} channel video start")
        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
        if channel.avatar is None:
            with get_session() as session:
                channel = session.query(Channel).filter(Channel.channel_id == channel.channel_id).first()
                channel.avatar = subscribe_channel.get_channel_info().avatar
                session.commit()
        # 下载全部的
        update_all = channel.if_download_all or channel.if_extract_all
        video_list = subscribe_channel.get_channel_videos(channel=channel, update_all=update_all)
        extract_video_list = []
        extract_download_video_list = []
        if channel.if_extract_all:
            if channel.if_auto_download:
                if channel.if_download_all:
                    extract_download_video_list = video_list
                else:
                    extract_video_list = video_list[GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE:]
                    extract_download_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list

        else:
            if channel.if_auto_download:
                extract_download_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]

        for video in extract_video_list:
            start(video, if_subscribe=True)
        for video in extract_download_video_list:
            start(video, if_only_extract=False, if_subscribe=True)
        logger.debug(f"update {channel.name} channel video end")


class RepairDownloadTaskInfo:

    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                download_tasks = session.query(DownloadTask).filter(DownloadTask.channel_name.is_(None)).all()
                for download_task in download_tasks:
                    if download_task.channel_name is not None:
                        continue

                    base_info = Downloader.get_video_info(download_task.url)
                    video = VideoFactory.create_video(download_task.url, base_info)
                    download_task.channel_id = video.get_uploader().id
                    download_task.channel_url = video.get_uploader().url
                    download_task.channel_name = video.get_uploader().name
                    download_task.channel_avatar = video.get_uploader().avatar
                    session.commit()

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


class RepairChanelInfoForTotalVideos:

    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                channels = session.query(Channel).all()
                for channel in channels:
                    extract_count = session.query(ChannelVideo).filter(ChannelVideo.channel_id == channel.channel_id).count()
                    if channel.total_videos >= extract_count:
                        continue
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
                    videos = subscribe_channel.get_channel_videos(channel, update_all=True)
                    channel.total_videos = len(videos)
                    session.commit()

        except json.JSONDecodeError as e:
            # 特定地捕获JSON解码错误
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            # 捕获其他所有异常
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


class RepairChannelVideoDuration:

    @classmethod
    def run(cls):
        url = ''
        with get_session() as session:
            channel_videos = session.query(ChannelVideo).filter(ChannelVideo.duration == None).order_by(
                ChannelVideo.created_at.desc()).all()
            for channel_video in channel_videos:
                try:
                    if channel_video.duration is not None:
                        continue
                    url = channel_video.url
                    video = VideoFactory.create_video(url, None)
                    if not video.video_exists():
                        logger.info(f"video not exists: {url}")
                        continue

                    base_info = Downloader.get_video_info(url)
                    video = VideoFactory.create_video(url, base_info)
                    # 随机休眠1-3秒
                    time.sleep(random.randint(1, 2))

                    if base_info is None or video.get_duration() is None:
                        continue
                    channel_video.duration = video.get_duration()
                    session.commit()
                except json.JSONDecodeError as e:
                    # 特定地捕获JSON解码错误
                    logger.error(f"Error decoding JSON: {e}", exc_info=True)
                except Exception as e:
                    # 捕获其他所有异常
                    logger.error(f"An unexpected error occurred: url: {url}, {e}", url, exc_info=True)

