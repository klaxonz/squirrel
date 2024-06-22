
import requests
from yt_dlp import YoutubeDL
from ..common.config import GlobalConfig
from ..common.cache import RedisClient
from ..meta.video import VideoFactory, Video
from ..nfo.nfo import NfoGenerator
import logging

class Downloader:
    
    @staticmethod
    def on_progress_hook(d):
        """
        回调函数，用于处理下载进度信息并更新到Redis。
        """
        if d['status'] == 'downloading':
            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes', None)
            speed = d.get('_speed_str', '')
            eta = d.get('_eta_str', '')

            # 处理可能的None值，避免错误
            total_bytes = total_bytes if total_bytes is not None else 'unknown'
            eta = eta if eta != '00:00' else 'unknown'  # 或者根据需要处理为具体文案，如'即将完成'

            # 构建进度信息字典
            progress_info = {
                'downloaded_bytes': downloaded_bytes,
                'total_bytes': total_bytes,
                'speed': speed,
                'eta': eta
            }

            video_id = d['info_dict']['id']
            redis_client.hmset(f'download_stats:{video_id}', progress_info)
          
        
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
    def download_avatar(video: Video) -> bool:
        response = requests.get(video.get_uploader().get_avatar())
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
        }
        
        cookie_file_path = GlobalConfig.get_cookies_file_path()
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path
            
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            Downloader.download_avatar(video)
            NfoGenerator.generate_nfo(video)
            