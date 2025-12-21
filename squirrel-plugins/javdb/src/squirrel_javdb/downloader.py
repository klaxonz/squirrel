from __future__ import annotations

import datetime
from typing import Dict, Optional, Any

from bs4 import BeautifulSoup

from crawl import Downloader, register_downloader, AuthError, VipError, ParseError
from .browser_utils import fetch_page_html


@register_downloader
class JavdbDownloader:
    """JavDB下载器，实现Downloader Protocol"""

    domains = ['javdb.com']
    domain = 'javdb.com'

    def __init__(self, url: str):
        self.url = url
        self.domain = self.domains[0]

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        html = fetch_page_html(self.url)  # type: ignore
        soup = BeautifulSoup(html, 'html.parser')
        video_info: Dict[str, Any] = {}

        vip_keywords = ['永久VIP', 'Join VIP']
        login_keywords = ['欢迎登入','歡迎登入', 'requires login to view']
        if any(kw in html for kw in vip_keywords):
            raise VipError("需要永久VIP权限", context={"url": self.url, "reason": "vip_required"})
        if any(kw in html for kw in login_keywords):
            raise AuthError("需要登录访问", context={"url": self.url, "reason": "login_required"})

        title_nodes = soup.select('.title strong')
        if not title_nodes:
            raise ParseError("无法解析视频标题，页面结构可能已变化", context={"url": self.url, "reason": "title_not_found"})
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

    def download(
        self,
        subscription: Any,
        video: Any,
        task: Any,
        queue_thread_name: str,
        video_info: Optional[Any] = None,
    ) -> Any:
        """执行下载工作流"""
        raise NotImplementedError("Download handled by backend download service")


