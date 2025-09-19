import datetime
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from common.http_wrapper import session
from sites.downloader import Downloader
from models.task.download_task import DownloadTask
from models.subscription import Subscription
from models.video import Video
from models.task.task_state import TaskState
from sites.downloader_registry import register_downloader

logger = logging.getLogger()


@register_downloader
class JavdbDownloader(Downloader):
    domain = 'javdb.com'

    def get_video_info(self, queue_name: str = None) -> Optional[Dict[str, Any]]:
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
        }
        response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        video_info: Dict[str, Any] = {}

        if '永久VIP' in response.text:
            logger.info(f'{self.url} is permanent VIP')
            return None
        if '此內容需要登入' in response.text:
            logger.info(f'{self.url} is need to login to pay, skip')
            return None

        title_nodes = soup.select('.title strong')
        if not title_nodes:
            logger.error('Failed to find title nodes on page')
            return None
        title_parts = [t.get_text(strip=True) for t in title_nodes if t.get_text(strip=True)]
        video_info['title'] = ' '.join(title_parts) if title_parts else None

        thumb_nodes = soup.select('.video-cover')
        if thumb_nodes and thumb_nodes[0].has_attr('src'):
            raw_src = thumb_nodes[0]['src']
            video_info['thumbnail'] = urljoin(self.url, raw_src)
        else:
            video_info['thumbnail'] = None

        try:
            duration_node = soup.select_one('.movie-panel-info .panel-block:nth-of-type(3) span')
            if duration_node:
                duration_text = duration_node.get_text(strip=True).split(' ')[0]
                video_info['duration'] = int(duration_text) * 60
            else:
                video_info['duration'] = None
        except Exception:
            video_info['duration'] = None

        try:
            date_node = soup.select_one('.movie-panel-info .panel-block:nth-of-type(2) span')
            if date_node:
                ts = int(datetime.datetime.strptime(date_node.get_text(strip=True), '%Y-%m-%d').timestamp())
                video_info['timestamp'] = ts
            else:
                video_info['timestamp'] = None
        except Exception:
            video_info['timestamp'] = None
        return video_info

    def download(self, subscription: Subscription, video: Video, task: DownloadTask, queue_thread_name: str,
                 video_info: Optional[Dict[str, Any]] = None) -> TaskState:
        if video_info is None:
            video_info = self.get_video_info(queue_thread_name)
        if not video_info:
            logger.error(f"Failed to parse video info: {video.url}")
            return TaskState.FAILED

        return super().download(subscription, video, task, queue_thread_name, video_info=video_info)
