from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from crawl import request_without_limit


def fetch_html(link: str) -> str:
	response = request_without_limit('GET', link, bypass_mode="mirror")
	return response.text


class JavdbHandler:
    """JavDB视频URL处理器，实现VideoUrlHandler Protocol"""

    domain = 'javdb.com'

    def get_video_url(self, video: Any) -> dict:
        no = str(getattr(video, 'title', '')).split(' ')[0]
        stream_info = self._get_jav_video_stream(no)
        if not stream_info:
            return {'video_url': None, 'audio_url': None}

        stream_url, referer = stream_info
        return {
            'video_url': self._build_proxy_url(stream_url, referer),
            'audio_url': None,
        }

    def _build_proxy_url(self, stream_url: str, referer: Optional[str] = None) -> str:
        query = {
            'domain': self.domain,
            'url': stream_url,
        }
        if referer:
            query['referer'] = referer
        return f'/api/video/proxy?{urlencode(query)}'

    def _get_jav_video_stream(self, no: str) -> Optional[tuple[str, str]]:
        try:
            url = f'https://missav.ai/search/{no}'
            html = fetch_html(url)
            bs4 = BeautifulSoup(html, 'html.parser')
            items = bs4.select('div.thumbnail')
            if not items:
                return None

            target = items[0]
            a_el = target.select_one('a')
            if not a_el:
                return None

            target_url = a_el.get('href')
            if not isinstance(target_url, str) or not target_url.startswith('http'):
                return None

            html = fetch_html(target_url)
            parts = self._extract_parts_from_html_content(html)
            if not parts:
                return None

            url_path = parts.split('m3u8|')[1].split('|playlist|source')[0]
            url_words = url_path.split('|')
            video_index = url_words.index('video')
            protocol = url_words[video_index - 1]
            video_format = url_words[video_index + 1]
            m3u8_url_path = '-'.join((url_words[0:5])[::-1])
            base_url_path = '.'.join((url_words[5:video_index - 1])[::-1])
            formatted_url = '{0}://{1}/{2}/{3}/{4}.m3u8'.format(
                protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index]
            )
            return formatted_url, target_url
        except Exception:
            return None

    def _get_jav_video_url(self, no: str) -> Optional[str]:
        stream_info = self._get_jav_video_stream(no)
        return stream_info[0] if stream_info else None

    def _extract_parts_from_html_content(self, html_content: str) -> Optional[str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup.find_all('script'):
            if script.string and 'm3u8|' in script.string:
                pattern = r"'([^']*m3u8\|[^']*)'"
                match = re.search(pattern, script.string)
                if match:
                    return match.group(1)
        return None
