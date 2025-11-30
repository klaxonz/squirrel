from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from botasaurus.browser import browser as bbrowser, Driver

from crawl import VideoUrlHandler, register_handler


DEBUG_BROWSER = os.getenv("JAVDB_DEBUG_BROWSER") == "1"


@bbrowser(
	output=None,
	raise_exception=True,
	close_on_crash=True,
	create_error_logs=False,
	max_retry=3,
	reuse_driver=False,
	block_images_and_css=True,
    headless=True
)
def _fetch_html(driver: Driver, link: str) -> str:
	# When debugging, load the page in the real browser as well.
	if driver.config.is_new:
		# First hit goes through Google referrer to clear Cloudflare checks.
		driver.google_get(link, bypass_cloudflare=True)
	response = driver.requests.get(link)
	response.raise_for_status()
	if DEBUG_BROWSER:
		driver.prompt()
	return response.text


def fetch_html(link: str) -> str:
	return _fetch_html(link)  # type: ignore


@register_handler
class JavdbHandler(VideoUrlHandler):
	domain = 'javdb.com'

	def get_video_url(self, video) -> dict:
		proxy_prefix_path = f"/api/video/proxy?domain=javdb.com"
		no = str(getattr(video, 'title', '')).split(' ')[0]
		url = self._get_jav_video_url(no)
		if url:
			return {
				"video_url": f"{proxy_prefix_path}&url=" + quote(url),
				"audio_url": None,
			}
		return {"video_url": None, "audio_url": None}

	def _get_jav_video_url(self, no: str) -> Optional[str]:
		try:
			url = f'https://missav.ws/search/{no}'
			html = fetch_html(url)
			bs4 = BeautifulSoup(html, 'html.parser')
			items = bs4.select('div.thumbnail')
			if len(items) > 0:
				target = items[0]
				a_el = target.select_one('a')
				if not a_el:
					return None
				target_url = a_el.get('href')
				if not isinstance(target_url, str) or not target_url.startswith('http'):
					return None
				html = fetch_html(target_url)
				r = self._extract_parts_from_html_content(html)
				if not r:
					return None
				url_path = r.split("m3u8|")[1].split("|playlist|source")[0]
				url_words = url_path.split('|')
				video_index = url_words.index("video")
				protocol = url_words[video_index - 1]
				video_format = url_words[video_index + 1]
				m3u8_url_path = "-".join((url_words[0:5])[::-1])
				base_url_path = ".".join((url_words[5:video_index - 1])[::-1])
				formatted_url = "{0}://{1}/{2}/{3}/{4}.m3u8".format(
					protocol, base_url_path, m3u8_url_path, video_format, url_words[video_index]
				)
				return formatted_url
			return None
		except Exception:
			return None

	def _extract_parts_from_html_content(self, html_content: str) -> Optional[str]:
		soup = BeautifulSoup(html_content, 'html.parser')
		for script in soup.find_all('script'):
			if script.string and 'm3u8|' in script.string:
				pattern = r"'([^']*m3u8\|[^']*)'"
				match = re.search(pattern, script.string)
				if match:
					return match.group(1)
		return None
