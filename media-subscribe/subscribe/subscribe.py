import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pytubefix import Channel as YouTubeChannel

from utils.cookie import filter_cookies_to_query_string
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
        match = re.search(r'/(\d+)(?:\?.*)?', self.url)
        if not match:
            raise Exception('Invalid url')

        return match.group(1)

    def get_channel_info(self):
        mid = self.get_mid()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        resp = session.get(self.url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 提取频道名称
        title_tag = soup.find('title')
        if title_tag:
            channel_name = title_tag.text.split('的个人空间')[0]
        else:
            channel_name = None

        # 提取头像图片 URL
        avatar_link = soup.find('link', rel='apple-touch-icon')
        if avatar_link:
            avatar_url = avatar_link.get('href')
            if avatar_url.startswith('//'):
                avatar_url = 'https:' + avatar_url
        else:
            avatar_url = None

        return ChannelMeta(mid, channel_name, avatar_url, self.url)

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


class PornhubSubscribeChannel(SubscribeChannel):
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

        bs4 = BeautifulSoup(response.text, 'html.parser')
        channel_els = bs4.select('#channelsProfile .title > h1')
        if len(channel_els) > 0:
            name = channel_els[0].text.strip()
            subscribe_url = bs4.select('button[data-subscribe-url]')[0].get('data-subscribe-url')
            channel_id = re.search(r"id=([^&]+)", subscribe_url).group(1)
        else:
            channel_id = None
            name = bs4.select('.nameSubscribe .name h1')[0].text.strip()
            add_friend_btn = bs4.select('.addFriendButton button[data-friend-url]')
            if len(add_friend_btn) > 0:
                channel_id = add_friend_btn[0].get('data-id')
            if channel_id is None:
                subscribe_btn = bs4.select('.subscribeButton button[data-subscribe-url]')
                if len(subscribe_btn) > 0:
                    channel_id = re.search(r"id=([^&]+)", subscribe_btn[0].get('data-subscribe-url')).group(1)

        url = re.search(r"^(.*?)(\?.*)?$", self.url).group(1)

        avatar = None
        avatar_els = bs4.select('#getAvatar')
        if len(avatar_els) > 0:
            avatar = avatar_els[0].get('src')
        if avatar is None:
            avatar_els = bs4.select('.topProfileHeader .thumbImage img')
            if len(avatar_els) > 0:
                avatar = avatar_els[0].get('src')

        return ChannelMeta(channel_id, name, avatar, url)

    def get_channel_videos(self, channel: Channel, update_all: bool):

        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }

        if 'pornhub.com/model' in self.url or 'pornhub.com/pornstar' in self.url:
            self.url = self.url + '/videos'

        response = session.get(self.url, headers=headers, timeout=15)
        if response.status_code == 404:
            self.url = self.url.replace('/videos', '')
            response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        video_list = []
        bs4 = BeautifulSoup(response.text, 'html.parser')
        page_next_list = bs4.select('.page_next')
        page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1
        current_page = 1

        while True:
            response = session.get(self.url + f'?page={current_page}', headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            video_els = []
            video_els.extend(bs4.select('#channelsProfile .videos a.videoPreviewBg'))
            video_els.extend(bs4.select('#profileContent .videos a.videoPreviewBg'))
            video_els.extend(bs4.select('#pornstarsVideoSection .videoPreviewBg'))
            for el in video_els:
                video_list.append(f'{base_url}{el["href"]}')

            new_page = int(bs4.select('.page_next')[0].find_previous().text) if len(page_next_list) > 0 else 1

            if new_page > page:
                page = new_page
            if current_page == page:
                break
            if not update_all:
                break
            current_page += 1

        return video_list


class SubscribeChannelFactory:

    @staticmethod
    def create_subscribe_channel(url):
        if 'bilibili.com' in url:
            return BilibiliSubscribeChannel(url)
        elif 'youtube.com' in url:
            return YouTubeSubscribeChannel(url)
        elif 'pornhub.com' in url:
            return PornhubSubscribeChannel(url)
        else:
            raise Exception('Unsupported url')
