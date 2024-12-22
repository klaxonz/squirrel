import datetime
import logging
import os

import requests
import yt_dlp
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL

from common import constants
from common.http_wrapper import session
from core.cache import RedisClient
from core.database import get_session
from core.config import settings
from downloader.id_extractor import extract_id_from_url
from meta.base import Video
from meta.factory import VideoFactory
from models.download_task import DownloadTask
from nfo.nfo import NfoGenerator

logger = logging.getLogger()


class DownloadStoppedError(Exception):
    """Exception raised when the download is intentionally stopped."""
    pass


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


class Downloader:

    @staticmethod
    def get_video_info(url):
        if 'javdb.com' in url:
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
            }
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            video_info = {}

            if '永久VIP' in response.text:
                logger.info(f'{url} is permanent VIP')
                return None

            video_info['title'] = bs4.select('.title strong')[0].text.strip() + ' ' + bs4.select('.title strong')[1].text.strip()
            video_info['thumbnail'] = bs4.select('.video-cover')[0]['src']
            duration = bs4.select('.movie-panel-info .panel-block:nth-of-type(3) span')[0].text.split(' ')[0].strip()
            try:
                video_info['duration'] = int(duration) * 60
            except ValueError:
                video_info['duration'] = None
            video_info['id'] = extract_id_from_url(url)
            video_info['timestamp'] = int(datetime.datetime.strptime(bs4.select('.movie-panel-info .panel-block:nth-of-type(2) span')[0].text.strip(), '%Y-%m-%d').timestamp())
            return video_info
        else:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'skip_download': True,
            }
            cookie_file_path = settings.get_cookies_file_path()
            if cookie_file_path:
                ydl_opts['cookiefile'] = cookie_file_path

            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                return video_info

    @staticmethod
    def get_video_info_thread(url: str, queue_thread_name: str):
        if 'javdb.com' in url:
            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/124.0.0.0 Safari/537.36',
            }
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            video_info = {}

            if '永久VIP' in response.text:
                logger.info(f'{url} is permanent VIP')
                return None

            video_info['title'] = bs4.select('.title strong')[0].text.strip() + ' ' + bs4.select('.title strong')[1].text.strip()
            video_info['thumbnail'] = bs4.select('.video-cover')[0]['src']
            duration = bs4.select('.movie-panel-info .panel-block:nth-of-type(3) span')[0].text.split(' ')[0].strip()
            try:
                video_info['duration'] = int(duration) * 60
            except ValueError:
                video_info['duration'] = None
            video_info['id'] = extract_id_from_url(url)
            video_info['timestamp'] = int(datetime.datetime.strptime(bs4.select('.movie-panel-info .panel-block:nth-of-type(2) span')[0].text.strip(), '%Y-%m-%d').timestamp())
            return video_info
        else:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'skip_download': True,
            }
            cookie_file_path = settings.get_cookies_file_path_thread(queue_thread_name)
            if cookie_file_path:
                ydl_opts['cookiefile'] = cookie_file_path

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(url, download=False)
                    return video_info
            except yt_dlp.utils.DownloadError as de:
                logger.error(f"解析视频信息失败: {url}, error: {de.msg}")
                return None
            except Exception:
                logger.error(f"解析视频信息失败: {url}", exc_info=True)
                return None

    @staticmethod
    def download_avatar(video: Video):
        response = requests.get(video.actors.avatar, timeout=15)
        response.raise_for_status()
        download_path = video.get_tv_show_root_path()
        download_fullpath = f'{download_path}/poster.jpg'
        with open(download_fullpath, 'wb') as file:
            file.write(response.content)

    @staticmethod
    def download(task_id: int, url: str, queue_thread_name: str):
        base_info = Downloader.get_video_info_thread(url, queue_thread_name)
        video = VideoFactory.create_video(url, base_info)
        if not video:
            logging.error(f"解析视频信息失败: {url}", )
            return

        hook = create_progress_hook(task_id)
        output_dir = video.get_download_full_path()
        filename = video.get_valid_filename()
        ydl_opts = {
            'writethumbnail': f'{output_dir}/{filename}.jpg',
            'outtmpl': f'{output_dir}/{filename}.%(ext)s',
            'progress_hooks': [hook],
            'writesubtitles': True,
            'subtitleslangs': ['zh-Hans', 'zh-Hant', 'en']
        }

        cookie_file_path = settings.get_cookies_file_path_thread(queue_thread_name)
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                Downloader.download_avatar(video)
                NfoGenerator.generate_nfo(video)

                ext_names = ['.mp4', '.mkv', '.webm']
                files = os.listdir(output_dir)
                filepath = None
                for file in files:
                    if file.startswith(filename) and any(file.endswith(ext) for ext in ext_names):
                        filepath = os.path.join(output_dir, file)
                        break
                if filepath:
                    # 获取文件大小
                    file_size = os.path.getsize(filepath)

                    # 更新文件大小到 Redis 缓存
                    redis_client = RedisClient.get_instance().client
                    redis_client.hset(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'total_size',
                                      file_size)

                    video_id = extract_id_from_url(url)

                    with get_session() as session:
                        session.query(DownloadTask).filter(DownloadTask.video_id == video_id).update({
                            'total_size': file_size
                        })
                        session.commit()
        except DownloadStoppedError:
            logging.info(f"下载视频被停止: {url}")
            return 2
        except Exception:
            logging.error(f"下载视频失败: {url}", exc_info=True)
            return 1
        return 0
