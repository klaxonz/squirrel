from __future__ import annotations

import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

from crawl import (
    register_subscription,
    SubscriptionMeta,
    filter_cookies_to_query_string,
)
from .sign import sign


logger = logging.getLogger(__name__)


@register_subscription("bilibili", ["bilibili.com"])
class BilibiliSubscription:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_mid(self) -> str:
        match = re.search(r'/([0-9]+)(?:\?.*)?$', self.url)
        if not match:
            raise ValueError('Invalid bilibili space url')
        return match.group(1)

    def get_subscribe_info(self) -> SubscriptionMeta:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            "Referer": self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        resp = requests.get(self.url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        title_tag = soup.find('title')
        channel_name = title_tag.text.split('的个人空间')[0] if title_tag and title_tag.text else None

        avatar_link = soup.find('link', rel='apple-touch-icon')
        avatar_url = None
        if avatar_link:
            avatar_url = avatar_link.get('href')
            if avatar_url and avatar_url.startswith('//'):
                avatar_url = 'https:' + avatar_url

        return SubscriptionMeta(self.get_mid(), channel_name, avatar_url, self.url)

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }

        params = {
            'mid': self.get_mid(),
            'ps': '50',
            'pn': '1',
            'index': '1',
            'order': 'pubdate',
            'platform': 'web',
            'web_location': '1550101'
        }
        video_list: List[str] = []

        should_continue = True
        while should_continue:
            query = sign(params)
            req_url = f'https://api.bilibili.com/x/space/wbi/arc/search?{query}'
            resp = requests.get(req_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                raise RuntimeError('Request failed')

            info = resp.json()
            page = info['data']['page']
            total_page = page['count'] / page['ps']

            for v in info['data']['list']['vlist']:
                if v.get('is_union_video') == 1:
                    continue
                video_list.append(f'https://www.bilibili.com/video/{v["bvid"]}')

            if int(params['pn']) < int(total_page) + 1:
                params['pn'] = str(int(params['pn']) + 1)
            else:
                should_continue = False

            if not extract_all:
                should_continue = False

        return video_list


