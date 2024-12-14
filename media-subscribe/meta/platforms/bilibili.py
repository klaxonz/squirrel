import json
import logging
import re
from utils.cookie import filter_cookies_to_query_string
from common.http_wrapper import session
from ..base import Video, Uploader

logger = logging.getLogger()

class BilibiliVideo(Video):
    DOMAIN = 'bilibili.com'

    def video_exists(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers)
        return '视频去哪了' not in response.text

class BilibiliUploader(Uploader):
    DOMAIN = 'bilibili.com'

    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }

        # 发送带有请求头的HTTP GET请求
        response = session.get(self.url, headers=headers, timeout=20)
        response.raise_for_status()  # 检查请求是否成功

        match = re.search(r'window\.__INITIAL_STATE__=(\{.*?\});', response.text)

        if match:
            json_str = match.group(1)  # 提取 JSON 字符串
            data = json.loads(json_str)

            if 'videoStaffs' in data:
                logger.info(f"Not a normal video. url: {self.url}")
                return

            if data.get('upData') is None:
                logger.info(f"Failed to extract data from the response. url: {self.url}")
                return

            self.id = data.get('upData').get('mid')
            self.name = data.get('upData').get('name')
            self.avatar = data.get('upData').get('face')
            self.tags = []

            tags = data.get('tags')
            for tag in tags:
                self.tags.append(tag.get('tag_name'))