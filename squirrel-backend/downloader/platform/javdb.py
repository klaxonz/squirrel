import datetime
import logging
from typing import Optional

from bs4 import BeautifulSoup
from botasaurus.request import request as brequest, Request

from downloader.platform.base import Downloader
from models.task.download_task import DownloadTask
from models.subscription import Subscription
from models.video import Video
from models.task.task_state import TaskState

logger = logging.getLogger()


@brequest(output=None, raise_exception=True, close_on_crash=True, create_error_logs=False, max_retry=10)
def _fetch_html(req: Request, link: str) -> str:
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    resp = req.get(link, timeout=20, headers=headers)
    resp.raise_for_status()
    return resp.text


def fetch_html(link: str) -> str:
    return _fetch_html(link)  # type: ignore


class JavdbDownloader(Downloader):

    def get_video_info(self, url: str, queue_name: Optional[str] = None):
        html = fetch_html(url)
        bs4 = BeautifulSoup(html, 'html.parser')
        video_info = {}

        if '永久VIP' in html:
            logger.info(f'{url} is permanent VIP')
            return None
        if '此內容需要登入' in html:
            logger.info(f'{url} is need to login to pay, skip')
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

    def download(self, subscription: Subscription, video: Video, task: DownloadTask, queue_thread_name: str) -> TaskState:
        # First get video info using our custom method
        video_info = self.get_video_info(video.url, queue_thread_name)
        if not video_info:
            logging.error(f"Failed to parse video info: {video.url}")
            return TaskState.FAILED

        # Then use the base class download implementation
        return super().download(subscription, video, task, queue_thread_name)
