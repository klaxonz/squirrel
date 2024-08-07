import json
import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common.http_wrapper import session
from .bilibili_sign import sign
from common.cookie import filter_cookies_to_query_string
from meta.channel import ChannelMeta
from model.channel import Channel

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
                if 'season_id' in v:
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

    def get_channel_info(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        match = re.search(r'var ytInitialData = (\{.*?\});', response.text)
        if not match:
            raise Exception('Fetch channel info failed')

        json_str = match.group(1)
        data = json.loads(json_str)

        channel_id = data['metadata']['channelMetadataRenderer']['externalId']
        name = data['metadata']['channelMetadataRenderer']['title']
        avatar = data['metadata']['channelMetadataRenderer']['avatar']['thumbnails'][-1]['url']
        return ChannelMeta(channel_id, name, avatar, self.url)

    def get_channel_videos(self, channel: Channel, update_all: bool):
        channel_id = "UU" + channel.channel_id[2:]

        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        playlist_url = f'https://www.youtube.com/playlist?list={channel_id}'

        response = session.get(playlist_url, headers=headers, timeout=15)
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

        while len(origin_video_list) == 101:
            v = origin_video_list[100]
            click_tracking_params = v["continuationItemRenderer"]['continuationEndpoint']['clickTrackingParams']
            continuation = v['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
            url = "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false"
            payload = json.dumps({
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20240719.00.00"
                    },
                    "clickTracking": {
                        "clickTrackingParams": click_tracking_params
                    }
                },
                "continuation": continuation
            })
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,zh-Hans;q=0.8,en;q=0.7,zh-Hant;q=0.6,ja;q=0.5,und;q=0.4,de;q=0.3,fr;q=0.2,cy;q=0.1',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            }

            response = session.post(url, headers=headers, data=payload)
            response.raise_for_status()

            continuation_response = json.loads(response.text)
            origin_video_list = continuation_response['onResponseReceivedActions'][0]['appendContinuationItemsAction'][
                'continuationItems']

            for v in origin_video_list:
                if 'playlistVideoRenderer' in v:
                    video_id = v["playlistVideoRenderer"]['videoId']
                    video_list.append(f'https://www.youtube.com/watch?v={video_id}')

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
