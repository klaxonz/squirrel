import logging
import re

import requests
from bs4 import BeautifulSoup

from common.http_wrapper import session
from meta.channel import SubscriptionMeta
from utils.cookie import filter_cookies_to_query_string
from .sign import sign
from ...base import BaseSubscription

logger = logging.getLogger()


class BilibiliSubscription(BaseSubscription):
    DOMAIN = 'bilibili.com'

    def get_mid(self):
        match = re.search(r'/(\d+)(?:\?.*)?', self.url)
        if not match:
            raise Exception('Invalid url')
        return match.group(1)

    def get_subscribe_info(self):
        mid = self.get_mid()
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        resp = session.get(self.url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        title_tag = soup.find('title')
        channel_name = title_tag.text.split('的个人空间')[0] if title_tag else None

        avatar_link = soup.find('link', rel='apple-touch-icon')
        avatar_url = None
        if avatar_link:
            avatar_url = avatar_link.get('href')
            if avatar_url.startswith('//'):
                avatar_url = 'https:' + avatar_url

        return SubscriptionMeta(mid, channel_name, avatar_url, self.url)

    def get_subscribe_videos(self, extract_all: bool):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
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

            for v in info['data']['list']['vlist']:
                if v['is_union_video'] == 1:
                    continue

                req_url = f'https://api.bilibili.com/x/web-interface/wbi/view?bvid={v["bvid"]}'
                resp = requests.get(req_url, headers=headers)
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

            if params['pn'] < int(total_page) + 1:
                params['pn'] += 1
            else:
                should_continue = False

            if not extract_all:
                should_continue = False

        return video_list
