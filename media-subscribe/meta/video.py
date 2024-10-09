import json
import logging
import os
import re

import requests
from pathvalidate import sanitize_filename
from pytubefix import YouTube

from utils.cookie import filter_cookies_to_query_string
from common.http_wrapper import session
from core.config import settings

logger = logging.getLogger(__name__)


class Video:

    def __init__(self, url, base_info):
        self.id = None
        self.url = url
        self.title = None
        self.description = None
        self.tags = None
        self.duration = None
        self.thumbnail = None
        self.upload_date = None
        self.uploader = None
        self.base_info = base_info
        self.uploader = None
        self.season = None

    def get_url(self):
        return self.url

    def get_uploader(self):
        if self.uploader is None:
            self.uploader = UploaderFactory.create_uploader(self.url)
        return self.uploader

    def get_title(self):
        if self.title is None:
            self.title = self.base_info.get("title")
        return self.title

    def get_description(self):
        if self.description is None:
            self.description = self.base_info.get("description")
        return self.description

    def get_thumbnail(self):
        if self.thumbnail is None:
            self.thumbnail = self.base_info.get("thumbnail")
        return self.thumbnail

    def get_upload_date(self):
        if self.upload_date is None:
            self.upload_date = self.base_info.get("upload_date")
        return self.upload_date

    def get_tags(self):
        if self.tags is None:
            self.tags = self.base_info.get("tags")
        return self.tags

    def get_duration(self):
        if self.duration is None:
            self.duration = self.base_info.get("duration")
        return self.duration

    def get_season(self):
        if self.season is None:
            self.season = self.get_upload_date()[0:4]
        return self.season

    def get_tv_show_root_path(self):
        root_path = settings.get_download_root_path()
        uploader_name = self.get_valid_uploader_name()
        return os.path.join(root_path, uploader_name)

    def get_download_full_path(self):
        root_path = settings.get_download_root_path()
        uploader_name = self.get_valid_uploader_name()
        season = self.get_season()

        return os.path.join(root_path, uploader_name, f"Season {season}")

    def get_valid_uploader_name(self):
        uploader_name = self.get_uploader().get_name()
        return sanitize_filename(uploader_name)

    def get_valid_filename(self):
        title = self.get_title()
        return sanitize_filename(title)

    def video_exists(self):
        return True


class BilibiliVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    def video_exists(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        response = requests.get(self.url, headers=headers)
        return '视频去哪了' not in response.text


class YoutubeVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)


class Uploader:
    def __init__(self, url):
        self.url = url
        self.id = None
        self.name = None
        self.avatar = None
        self.tags = None

    def get_id(self):
        return self.id

    def get_url(self):
        return self.url

    def get_name(self):
        return self.name

    def get_avatar(self):
        return self.avatar

    def get_tags(self):
        return self.tags


class BilibiliUploader(Uploader):
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
                logger.info(f"Failed to extract data from the response. url: {self.url}, text: {json_str}")
                return

            self.id = data.get('upData').get('mid')
            self.name = data.get('upData').get('name')
            self.avatar = data.get('upData').get('face')
            self.tags = []

            tags = data.get('tags')
            for tag in tags:
                self.tags.append(tag.get('tag_name'))


class YoutubeUploader(Uploader):
    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        video = YouTube(self.url, use_oauth=True, allow_oauth_cache=True, )
        self.id = video.channel_id
        self.name = video.author
        self.avatar = video.thumbnail_url
        self.tags = []


class VideoFactory:

    @staticmethod
    def create_video(url, video_info):
        if 'bilibili.com' in url:
            return BilibiliVideo(url, video_info)
        elif 'youtube.com' in url:
            return YoutubeVideo(url, video_info)


class UploaderFactory:

    @staticmethod
    def create_uploader(url):
        if 'bilibili.com' in url:
            return BilibiliUploader(url)
        elif 'youtube.com' in url:
            return YoutubeUploader(url)
