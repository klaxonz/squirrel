import requests
from yt_dlp import YoutubeDL

from common.config import GlobalConfig
from meta.video import VideoFactory, Video
from model.download_task import DownloadTask
from nfo.nfo import NfoGenerator
import logging


class Downloader:

    @staticmethod
    def on_progress_hook(video_info):
        """
        回调函数，用于处理下载进度信息并更新到Redis。
        """
        if video_info['status'] == 'downloading':
            downloaded_bytes = video_info.get('downloaded_bytes', 0)
            total_bytes = video_info.get('total_bytes', None)
            speed = video_info.get('_speed_str', '')
            eta = video_info.get('_eta_str', '')

            # 处理可能的None值，避免错误
            total_bytes = total_bytes if total_bytes is not None else 'unknown'
            eta = eta if eta != '00:00' else 'unknown'  # 或者根据需要处理为具体文案，如'即将完成'

            video_id = video_info['info_dict']['id']
            download_task = DownloadTask.select().where(DownloadTask.video_id == video_id).get()
            download_task.status = 'DOWNLOADING'
            download_task.total_size = total_bytes
            download_task.downloaded_size = downloaded_bytes
            download_task.speed = speed
            download_task.eta = eta
            download_task.save()

    @staticmethod
    def get_video_info(url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'skip_download': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)
            return video_info

    @staticmethod
    def download_avatar(video: Video):
        response = requests.get(video.get_uploader().get_avatar(), timeout=15)
        response.raise_for_status()
        download_path = video.get_tv_show_root_path()
        download_fullpath = f'{download_path}/poster.jpg'
        with open(download_fullpath, 'wb') as file:
            file.write(response.content)

    @staticmethod
    def download(url: str):
        base_info = Downloader.get_video_info(url)
        video = VideoFactory.create_video(url, base_info)
        if not video:
            logging.error(f"解析视频信息失败: {url}", )
            return

        output_dir = video.get_download_full_path()
        filename = video.get_valid_filename()
        ydl_opts = {
            'writethumbnail': f'{output_dir}/{filename}.jpg',
            'outtmpl': f'{output_dir}/{filename}.%(ext)s',
            'merge_output_format': 'mp4',
            'progress_hooks': [Downloader.on_progress_hook],
        }

        cookie_file_path = GlobalConfig.get_cookies_file_path()
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            Downloader.download_avatar(video)
            NfoGenerator.generate_nfo(video)
