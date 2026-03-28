from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from crawl import NetworkError, ParseError, request_without_limit


def fetch_html(link: str) -> str:
	response = request_without_limit('GET', link, bypass_mode="mirror")
	return response.text


class JavdbHandler:
    """JavDB视频URL处理器，实现VideoUrlHandler Protocol"""

    domain = 'javdb.com'

    def get_video_url(self, video: Any) -> dict:
        no = str(getattr(video, 'title', '')).split(' ')[0]
        stream_info = self._get_jav_video_stream(no)
        stream_url, referer = stream_info
        return {
            'video_url': self._build_proxy_url(stream_url, referer),
            'audio_url': None,
        }

    @staticmethod
    def _looks_like_challenge_page(html: str) -> bool:
        lowered = html.lower()
        return 'just a moment' in lowered and 'cf_chl_' in lowered

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
            if self._looks_like_challenge_page(html):
                raise NetworkError(f'MissAV mirror challenge blocked playback lookup: {url}', context={'url': url})
            bs4 = BeautifulSoup(html, 'html.parser')
            items = bs4.select('div.thumbnail')
            if not items:
                raise ParseError(f'No MissAV search results found for {no}', context={'video_no': no, 'url': url})

            target = items[0]
            a_el = target.select_one('a')
            if not a_el:
                raise ParseError(f'MissAV search result is missing a detail link for {no}', context={'video_no': no, 'url': url})

            target_url = a_el.get('href')
            if not isinstance(target_url, str) or not target_url.strip():
                raise ParseError(f'MissAV search result returned an empty detail link for {no}', context={'video_no': no, 'url': url})
            target_url = urljoin(url, target_url)
            if not target_url.startswith('http'):
                raise ParseError(f'MissAV detail link is invalid for {no}', context={'video_no': no, 'target_url': target_url})

            html = fetch_html(target_url)
            if self._looks_like_challenge_page(html):
                raise NetworkError(
                    f'MissAV mirror challenge blocked playback detail lookup: {target_url}',
                    context={'video_no': no, 'url': target_url},
                )
            parts = self._extract_parts_from_html_content(html)
            if not parts:
                raise ParseError(
                    f'MissAV detail page is missing stream metadata for {no}',
                    context={'video_no': no, 'url': target_url},
                )

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
        except (NetworkError, ParseError):
            raise
        except Exception as exc:
            raise ParseError(
                f'Failed to resolve JavDB playback stream for {no}',
                context={'video_no': no, 'exception_type': exc.__class__.__name__},
            ) from exc

    def _get_jav_video_url(self, no: str) -> Optional[str]:
        stream_info = self._get_jav_video_stream(no)
        return stream_info[0] if stream_info else None

    def _extract_parts_from_html_content(self, html_content: str) -> Optional[str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup.find_all('script'):
            script_text = script.string or script.get_text()
            if script_text and 'm3u8|' in script_text:
                pattern = r"'([^']*m3u8\|[^']*)'"
                match = re.search(pattern, script_text)
                if match:
                    return match.group(1)
        return None
