from __future__ import annotations

import json
import logging
import re
from typing import Optional

from crawl import register_meta, Video, Actor, filter_cookies_to_query_string, request, get_http_headers

logger = logging.getLogger(__name__)

SITE_SLUG = 'bilibili'


@register_meta
class BilibiliVideo(Video):
    domain = 'bilibili.com'

    @property
    def actors(self):  # type: ignore[override]
        if len(self._actors) == 0:
            owner = self._base_info.get("owner") or {}
            if owner.get('mid'):
                actor_url = f"https://space.bilibili.com/{owner.get('mid')}"
                actor = Actor(actor_url)
                actor.name = owner.get('name')
                actor.avatar = owner.get('face')
                self._actors.append(actor)
                return self._actors

            headers = get_http_headers(SITE_SLUG, {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/58.0.3029.110 Safari/537.3',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            })

            response = request('GET', self.url, headers=headers, timeout=20)
            response.raise_for_status()
            match = re.search(r'window\.__INITIAL_STATE__=(\{.*?\});', response.text)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                if 'videoStaffs' in data:
                    logger.info("[bilibili] skip staffs video: %s", self.url)
                    return self._actors
                up_data = data.get('upData') or {}
                if not up_data:
                    logger.info("[bilibili] no upData found: %s", self.url)
                    return self._actors
                actor_url = f"https://space.bilibili.com/{up_data.get('mid')}"
                actor = Actor(actor_url)
                actor.name = up_data.get('name')
                actor.avatar = up_data.get('face')
                self._actors.append(actor)
        return self._actors

    def video_exists(self) -> bool:
        cookies = filter_cookies_to_query_string(self.url)
        headers = get_http_headers(SITE_SLUG, {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        })
        headers['Cookie'] = cookies
        response = request('GET', self.url, headers=headers, timeout=20)
        return '视频去哪了' not in response.text


