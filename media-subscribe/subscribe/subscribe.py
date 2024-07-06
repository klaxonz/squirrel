import json
import re
import requests

from common.config import GlobalConfig
from .bilibili_sign import sign
from common.cookie import filter_cookies_to_query_string
from meta.channel import ChannelMeta
from model.channel import Channel


class SubscribeChannel:
    def __init__(self, url):
        self.url = url

    def get_channel_info(self):
        pass

    def get_channel_videos(self, update_all: bool):
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
        resp = requests.get(req_url, headers=headers)
        if resp.status_code != 200:
            raise Exception('Request failed')

        info = resp.json()

        return ChannelMeta(mid, info['data']['name'], self.url)

    def get_channel_videos(self, update_all: bool):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 ...',
            'Cookie': cookies
        }
        ps = 25 if update_all else GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE

        params = {
            'mid': self.get_mid(),
            'ps': ps,
            'pn': 1,
            'index': 1,
            'order': 'pubdate',
            'platform': 'web',
            'web_location': 1550101
        }
        video_list = []

        # 这里模拟"do"部分，至少执行一次
        should_continue = True
        while should_continue:
            query = sign(params)
            req_url = f'https://api.bilibili.com/x/space/wbi/arc/search?{query}'
            resp = requests.get(req_url, headers=headers)
            if resp.status_code != 200:
                raise Exception('Request failed')

            info = resp.json()
            page = info['data']['page']
            total_page = page['count'] / page['ps']

            origin_vlist = info['data']['list']['vlist']
            for v in origin_vlist:
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

    def get_channel_info(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = requests.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        match = re.search(r'var ytInitialData = (\{.*?\});', response.text)
        if not match:
            raise Exception('Fetch channel info failed')

        json_str = match.group(1)
        data = json.loads(json_str)

        channel_id = data['metadata']['channelMetadataRenderer']['externalId']
        name = data['metadata']['channelMetadataRenderer']['title']

        return ChannelMeta(channel_id, name, self.url)

    def get_channel_videos(self, update_all: bool):
        channel = Channel.select().where(Channel.url == self.url).get()
        channel_id = "UU" + channel.channel_id[2:]

        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        playlist_url = f'https://www.youtube.com/playlist?list={channel_id}'

        response = requests.get(playlist_url, headers=headers, timeout=15)
        response.raise_for_status()

        match = re.search(r'var ytInitialData = (\{.*?\});', response.text)
        if not match:
            raise Exception('Fetch channel info failed')

        json_str = match.group(1)
        data = json.loads(json_str)

        origin_video_list = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content'][
            'sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer'][
            'contents']

        video_list = []
        for v in origin_video_list:
            if 'playlistVideoRenderer' in v:
                video_id = v["playlistVideoRenderer"]['videoId']
                video_list.append(f'https://www.youtube.com/watch?v={video_id}')

        if not update_all:
            video_list = video_list[:GlobalConfig.CHANNEL_UPDATE_DEFAULT_SIZE]
        return video_list


class SubscribeChannelFactory:

    @staticmethod
    def create_subscribe_channel(url):
        if 'bilibili.com' in url:
            return BilibiliSubscribeChannel(url)
        elif 'youtube.com' in url:
            return YouTubeSubscribeChannel(url)
        else:
            raise Exception('Unsupported url')
