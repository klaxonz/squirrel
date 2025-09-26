from __future__ import annotations

import datetime
from typing import Dict, Optional, Any

from bs4 import BeautifulSoup

from crawl import BaseDownloader, register_downloader, request


@register_downloader
class JavdbDownloader(BaseDownloader):
    domain = 'javdb.com'

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
        response = request('GET', self.url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        video_info: Dict[str, Any] = {}

        if '永久VIP' in response.text:
            return None
        if '此內容需要登入' in response.text:
            return None

        title_nodes = soup.select('.title strong')
        if not title_nodes:
            return None
        title_parts = [t.get_text(strip=True) for t in title_nodes if t.get_text(strip=True)]
        video_info['title'] = ' '.join(title_parts) if title_parts else None

        thumb_nodes = soup.select('.video-cover')
        if thumb_nodes and thumb_nodes[0].has_attr('src'):
            raw_src = thumb_nodes[0]['src']
            if raw_src.startswith('http'):
                video_info['thumbnail'] = raw_src
            else:
                from urllib.parse import urljoin

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

    def download(self, subscription, video, task, queue_thread_name: str, video_info=None):  # pragma: no cover
        raise NotImplementedError("Download handled by backend download service")


