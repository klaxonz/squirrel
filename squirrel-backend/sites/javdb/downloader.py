import datetime
import logging

import requests
from bs4 import BeautifulSoup
from common.http_wrapper import session
from sites.downloader import Downloader
from models.task.download_task import DownloadTask
from models.subscription import Subscription
from models.video import Video
from sites.downloader_registry import register_downloader

logger = logging.getLogger()


@register_downloader
class JavdbDownloader(Downloader):
    domain = 'javdb.com'

    def get_video_info(self, queue_name: str = None):
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
        }
        response = requests.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()
        bs4 = BeautifulSoup(response.text, 'html.parser')
        video_info = {}

        if '永久VIP' in response.text:
            logger.info(f'{self.url} is permanent VIP')
            return None
        if '此內容需要登入' in response.text:
            logger.info(f'{self.url} is need to login to pay, skip')
            return None

        video_info['title'] = bs4.select('.title strong')[0].text.strip() + ' ' + bs4.select('.title strong')[1].text.strip()
        video_info['thumbnail'] = bs4.select('.video-cover')[0]['src']
        duration = bs4.select('.movie-panel-info .panel-block:nth-of-type(3) span')[0].text.split(' ')[0].strip()
        try:
            video_info['duration'] = int(duration) * 60
        except ValueError:
            video_info['duration'] = None
        video_info['timestamp'] = int(datetime.datetime.strptime(
            bs4.select('.movie-panel-info .panel-block:nth-of-type(2) span')[0].text.strip(),
            '%Y-%m-%d').timestamp())
        return video_info

    def download(self, subscription: Subscription, video: Video, task: DownloadTask, queue_thread_name: str):
        # First get video info using our custom method
        video_info = self.get_video_info(queue_thread_name)
        if not video_info:
            logging.error(f"Failed to parse video info: {video.url}")
            return 1

        # Then use the base class download implementation
        return super().download(subscription, video, task, queue_thread_name)
