from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from crawl import NetworkError, ParseError, request_without_limit

DEFAULT_JAVDB_PLAYBACK_LOOKUP_TIMEOUT_SECONDS = 30.0
DEFAULT_JAVDB_PLAYBACK_LOOKUP_ATTEMPTS = 3


def fetch_html(link: str) -> str:
	response = request_without_limit(
		'GET',
		link,
		timeout=DEFAULT_JAVDB_PLAYBACK_LOOKUP_TIMEOUT_SECONDS,
		bypass_mode='html',
	)
	return response.text


class JavdbHandler:
    """JavDB视频URL处理器，实现VideoUrlHandler Protocol"""

    domain = 'javdb.com'

    def get_video_url(self, video: Any) -> dict:
        no = self._extract_video_no(str(getattr(video, 'title', '')))
        stream_info = self._get_jav_video_stream(no)
        stream_url, referer = stream_info
        return {
            'video_url': self._build_proxy_url(stream_url, referer),
            'audio_url': None,
        }

    @staticmethod
    def _extract_video_no(title: str) -> str:
        normalized_title = str(title or '').strip()
        match = re.search(r'\b([A-Za-z]{2,10}-\d{2,})\b', normalized_title)
        if match:
            return match.group(1).upper()
        return normalized_title.split(' ')[0]

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
        last_error: NetworkError | ParseError | None = None
        for _ in range(DEFAULT_JAVDB_PLAYBACK_LOOKUP_ATTEMPTS):
            try:
                return self._get_jav_video_stream_once(no)
            except (NetworkError, ParseError) as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise ParseError(f'Failed to resolve JavDB playback stream for {no}', context={'video_no': no})

    def _get_jav_video_stream_once(self, no: str) -> tuple[str, str]:
        try:
            direct_url = f'https://missav.ai/{no.lower()}'
            html = fetch_html(direct_url)
            if self._looks_like_challenge_page(html):
                raise NetworkError(f'MissAV mirror challenge blocked playback detail lookup: {direct_url}', context={'url': direct_url})
            parts = self._extract_parts_from_html_content(html)
            if parts:
                return self._format_stream_url(parts), direct_url

            url = f'https://missav.ai/search/{no}'
            html = fetch_html(url)
            if self._looks_like_challenge_page(html):
                raise NetworkError(f'MissAV mirror challenge blocked playback lookup: {url}', context={'url': url})
            bs4 = BeautifulSoup(html, 'html.parser')
            items = bs4.select('div.thumbnail')
            if not items:
                raise ParseError(f'No MissAV search results found for {no}', context={'video_no': no, 'url': url})
            last_detail_error: NetworkError | ParseError | None = None

            for target in items:
                a_el = target.select_one('a')
                if not a_el:
                    last_detail_error = ParseError(
                        f'MissAV search result is missing a detail link for {no}',
                        context={'video_no': no, 'url': url},
                    )
                    continue

                target_url = a_el.get('href')
                if not isinstance(target_url, str) or not target_url.strip():
                    last_detail_error = ParseError(
                        f'MissAV search result returned an empty detail link for {no}',
                        context={'video_no': no, 'url': url},
                    )
                    continue

                target_url = urljoin(url, target_url)
                if not target_url.startswith('http'):
                    last_detail_error = ParseError(
                        f'MissAV detail link is invalid for {no}',
                        context={'video_no': no, 'target_url': target_url},
                    )
                    continue

                html = fetch_html(target_url)
                if self._looks_like_challenge_page(html):
                    raise NetworkError(
                        f'MissAV mirror challenge blocked playback detail lookup: {target_url}',
                        context={'video_no': no, 'url': target_url},
                    )

                parts = self._extract_parts_from_html_content(html)
                if not parts:
                    last_detail_error = ParseError(
                        f'MissAV detail page is missing stream metadata for {no}',
                        context={'video_no': no, 'url': target_url},
                    )
                    continue

                return self._format_stream_url(parts), target_url

            if last_detail_error is not None:
                raise last_detail_error
            raise ParseError(f'No usable MissAV detail page found for {no}', context={'video_no': no, 'url': url})
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

    @staticmethod
    def _format_stream_url(parts: str) -> str:
        url_path = parts.split('m3u8|')[1].split('|playlist|source')[0]
        url_words = url_path.split('|')
        video_index = url_words.index('video')
        protocol = url_words[video_index - 1]
        video_format = url_words[video_index + 1]
        m3u8_url_path = '-'.join((url_words[0:5])[::-1])
        base_url_path = '.'.join((url_words[5:video_index - 1])[::-1])
        return '{0}://{1}/{2}/{3}/{4}.m3u8'.format(
            protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index]
        )

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
