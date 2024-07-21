import os

import requests
from yt_dlp import YoutubeDL

from common.config import GlobalConfig
from common.database import get_session
from downloader.id_extractor import extract_id_from_url
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
            total_bytes = video_info.get('total_bytes', 0)
            speed = video_info.get('_speed_str', '')
            eta = video_info.get('_eta_str', '')
            percent = video_info.get('_percent_str', '')

            # 处理可能的None值，避免错误
            eta = eta if eta != '00:00' else 'unknown'

            if 'id' in video_info['info_dict']:
                video_id = video_info['info_dict']['id']

                with get_session() as session:
                    session.query(DownloadTask).filter(DownloadTask.video_id == video_id).update({
                        'downloaded_size': downloaded_bytes,
                        'total_size': total_bytes,
                        'speed': speed,
                        'eta': eta,
                        'percent': percent
                    })
                    session.commit()

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
            'writesubtitles': True,
            'subtitleslangs': ['zh-Hans', 'zh-Hant', 'en']
        }

        cookie_file_path = GlobalConfig.get_cookies_file_path()
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            Downloader.download_avatar(video)
            NfoGenerator.generate_nfo(video)

            filepath = os.path.join(output_dir, filename + '.mp4')
            # 获取文件大小
            file_size = os.path.getsize(filepath)
            video_id = extract_id_from_url(url)

            with get_session() as session:
                session.query(DownloadTask).filter(DownloadTask.video_id == video_id).update({
                    'total_size': file_size
                })
                session.commit()
