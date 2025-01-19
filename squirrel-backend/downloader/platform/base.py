import logging
import os

import requests
from yt_dlp import YoutubeDL

from common import constants
from common.video_stream import VideoStreamHandler
from core import download_config, config
from core.cache import RedisClient
from core.database import get_session
from meta.factory import VideoFactory
from models.subscription import Subscription
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from models.video import Video
from nfo.nfo import NfoGenerator

logger = logging.getLogger()


class DownloadStoppedError(Exception):
    """Exception raised when the download is intentionally stopped."""
    pass


class Downloader:

    def get_video_info(self, url, queue_name: str = None):
        cookie_file_path = config.get_cookies_file_path_thread(queue_name)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'skip_download': True,
        }
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            return video_info

    def download_avatar(self, subscription_name: str, subscription_avatar: str):
        response = requests.get(subscription_avatar, timeout=15)
        response.raise_for_status()
        download_path = download_config.get_tv_show_root_path(subscription_name)
        download_fullpath = f'{download_path}/poster.jpg'
        with open(download_fullpath, 'wb') as file:
            file.write(response.content)

    def download(self, subscription: Subscription, video: Video, task: DownloadTask, queue_thread_name: str) -> TaskState:
        video_info = self.get_video_info(video.url, queue_thread_name)
        video_meta = VideoFactory.create_video(video.url, video_info)

        hook = create_progress_hook(task.id)
        output_dir = download_config.get_download_full_path(subscription.name, video_meta.season)
        filename = download_config.get_valid_filename(video.title)
        ydl_opts = {
            'writethumbnail': f'{output_dir}/{filename}.jpg',
            'outtmpl': f'{output_dir}/{filename}.%(ext)s',
            'progress_hooks': [hook],
            'writesubtitles': True,
            'subtitleslangs': ['zh-Hans', 'zh-Hant', 'en']
        }

        cookie_file_path = config.get_cookies_file_path_thread(queue_thread_name)
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])
                self.download_avatar(subscription.name, subscription.avatar)
                NfoGenerator.generate_nfo(subscription.name, video_meta.title, video_meta.description,
                                          video_meta.thumbnail, video_meta.season)

                filepath = VideoStreamHandler.find_video_file(output_dir, filename)
                if filepath:
                    file_size = os.path.getsize(filepath)
                    redis_client = RedisClient.get_instance().client
                    redis_client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task.id}', 'total_size',
                                      file_size)

                    with get_session() as session:
                        session.query(DownloadTask).filter_by(id=task.id).update({
                           DownloadTask.total_size: file_size
                        })
                        session.commit()

            return TaskState.COMPLETED
        except DownloadStoppedError:
            logging.info(f"下载视频被停止: {video.url}")
            return TaskState.PAUSED
        except Exception:
            logging.error(f"下载视频失败: {video.url}", exc_info=True)
            return TaskState.FAILED


def create_progress_hook(task_id: int):
    def on_progress_hook(video_info):
        """
        回调函数，用于处理下载进度信息并更新到Redis。
        """
        if video_info['status'] == 'downloading':
            downloaded_bytes = video_info.get('downloaded_bytes', 0)
            total_bytes = video_info.get('total_bytes', 0)
            speed = video_info.get('_speed_str', '')
            eta = video_info.get('_eta_str', '')
            percent = video_info.get('_percent_str', '')

            # 区分视频和音频下载
            file_type = 'video' if video_info.get('info_dict', {}).get('vcodec') != 'none' else 'audio'

            # 处理可能的None值，避免错误
            eta = eta if eta != '00:00' else 'unknown'

            if 'id' in video_info['info_dict']:
                client = RedisClient.get_instance().client
                status = client.get(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_STATUS}:{task_id}')
                if status == 'stop':
                    client.delete(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_STATUS}:{task_id}')
                    raise DownloadStoppedError('Download stopped')

                # 更新Redis，只存储当前下载类型的信息
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'current_type', file_type)
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'downloaded_size',
                            downloaded_bytes)
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'total_size', total_bytes)
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'speed', speed)
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'eta', eta)
                client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'percent', percent)

    return on_progress_hook
