import logging
import re

from pytubefix import Channel as YouTubeChannel

from common.cookie import filter_cookies_to_query_string
from common.http_wrapper import session
from meta.channel import ChannelMeta
from model.channel import Channel
from .bilibili_sign import sign

logger = logging.getLogger(__name__)


class SubscribeChannel:
    def __init__(self, url):
        self.url = url

    def get_channel_info(self):
        pass

    def get_channel_videos(self, channel: Channel, update_all: bool):
        pass


class BilibiliSubscribeChannel(SubscribeChannel):
    def __init__(self, url):
        super().__init__(url)

    def get_mid(self):
        # 提取 mid
        match = re.search(r'/(\d+)$', self.url)
        if not match:
            raise Exception('Invalid url')

        return match.group(1)

    def get_channel_info(self):
        mid = self.get_mid()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        params = {
            'mid': self.get_mid()
        }
        query = sign(params)
        req_url = f'https://api.bilibili.com/x/space/wbi/acc/info?{query}'
        resp = session.get(req_url, headers=headers)
        if resp.status_code != 200:
            raise Exception('Request failed')

        info = resp.json()

        return ChannelMeta(mid, info['data']['name'], info['data']['face'], self.url)

    def get_channel_videos(self, channel: Channel, update_all: bool):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }

        params = {
            'mid': self.get_mid(),
            'ps': 25,
            'pn': 1,
            'index': 1,
            'order': 'pubdate',
            'platform': 'web',
            'web_location': 1550101
        }
        video_list = []

        should_continue = True
        while should_continue:
            query = sign(params)
            req_url = f'https://api.bilibili.com/x/space/wbi/arc/search?{query}'
            resp = session.get(req_url, headers=headers)
            if resp.status_code != 200:
                raise Exception('Request failed')

            info = resp.json()
            page = info['data']['page']
            total_page = page['count'] / page['ps']

            origin_vlist = info['data']['list']['vlist']
            for v in origin_vlist:
                if v['is_union_video'] == 1:
                    continue
                # if 'season_id' in v:
                #     continue

                # 如果是分P视频则不下载
                req_url = f'https://api.bilibili.com/x/web-interface/wbi/view?bvid={v["bvid"]}'
                resp = session.get(req_url, headers=headers)
                if resp.status_code != 200:
                    raise Exception('Request failed')

                resp_json = resp.json()
                if 'data' not in resp_json:
                    logger.error(resp.json())
                    continue
                video_info = resp.json()['data']
                if 'pages' in video_info and len(video_info['pages']) > 1:
                    continue

                video_list.append(f'https://www.bilibili.com/video/{v["bvid"]}')

            # 判断是否继续循环，类似于"while"条件
            if params['pn'] < int(total_page) + 1:
                params['pn'] += 1
            else:
                should_continue = False

            if not update_all:
                should_continue = False

        return video_list


class YouTubeSubscribeChannel(SubscribeChannel):
    def __init__(self, url):
        super().__init__(url)
        self.channel = YouTubeChannel(url)

    def get_channel_info(self):
        return ChannelMeta(self.channel.channel_id, self.channel.channel_name, self.channel.thumbnail_url, self.url)

    def get_channel_videos(self, channel: Channel, update_all: bool):
        videos_ = []
        if self.channel.videos:
            for video in self.channel.videos:
                if video and video.watch_url:
                    videos_.append(video.watch_url)
        shorts_ = []
        if self.channel.shorts:
            for short in self.channel.shorts:
                if short and short.watch_url:
                    shorts_.append(short.watch_url)
        return videos_ + shorts_


class SubscribeChannelFactory:

    @staticmethod
    def create_subscribe_channel(url):
        if 'bilibili.com' in url:
            return BilibiliSubscribeChannel(url)
        elif 'youtube.com' in url:
            return YouTubeSubscribeChannel(url)
        else:
            raise Exception('Unsupported url')
