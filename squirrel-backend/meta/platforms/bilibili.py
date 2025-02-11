import json
import logging
import re

from common.http_wrapper import session
from utils.cookie import filter_cookies_to_query_string
from ..base import Video, Actor

logger = logging.getLogger()


class BilibiliVideo(Video):
    DOMAIN = 'bilibili.com'

    @property
    def actors(self):
        if len(self._actors) == 0:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/58.0.3029.110 Safari/537.3',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            }

            response = session.get(self.url, headers=headers, timeout=20)
            response.raise_for_status()
            match = re.search(r'window\.__INITIAL_STATE__=(\{.*?\});', response.text)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                if 'videoStaffs' in data:
                    logger.info(f"Not a normal video. url: {self.url}")
                    return self._actors
                if data.get('upData') is None:
                    logger.info(f"Failed to extract data from the response. url: {self.url}")
                    return self._actors
                actor_url = f"https://space.bilibili.com/{data.get('upData').get('mid')}"
                actor = Actor(actor_url)
                actor.name = data.get('upData').get('name')
                actor.avatar = data.get('upData').get('face')
                self._actors.append(actor)
        return self._actors

    def video_exists(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers)
        return '视频去哪了' not in response.text
