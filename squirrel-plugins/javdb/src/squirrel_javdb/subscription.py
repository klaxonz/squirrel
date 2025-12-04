from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from crawl import register_subscription, SubscriptionMeta
from .browser_utils import fetch_page_html


@register_subscription("javdb", ["javdb.com"])
class JavdbSubscription:
    def __init__(self, url: str) -> None:
        self.url = url

    def get_subscribe_info(self) -> SubscriptionMeta:
        html = fetch_page_html(self.url)  # type: ignore
        bs4 = BeautifulSoup(html, 'html.parser')
        username_el = bs4.select('.actor-section-name')
        if len(username_el) == 0:
            raise Exception(f'Can not find channel name in {self.url}')

        name = username_el[0].text.strip()
        if ',' in name:
            name = name.split(',')[0]

        avatar_el = bs4.select('.avatar')[0]
        style = avatar_el['style']
        avatar_match = re.search(r'url\((.*?)\)', style)
        avatar = avatar_match.group(1) if avatar_match else None
        channel_id = self.url.split('/')[-1]

        return SubscriptionMeta(channel_id, name, avatar, self.url)

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        html = fetch_page_html(self.url)  # type: ignore
        
        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list: List[str] = []

        bs4 = BeautifulSoup(html, 'html.parser')
        self._extract_video_urls(bs4, base_url, video_list)

        page_next_list = bs4.select('a.pagination-link[rel="next"]')
        page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
        current_page = 1

        while current_page < page and extract_all:
            current_page += 1
            page_html = fetch_page_html(self.url + f'?page={current_page}&sort_type=0')  # type: ignore
            bs4 = BeautifulSoup(page_html, 'html.parser')

            self._extract_video_urls(bs4, base_url, video_list)

            page_next_list = bs4.select('a.pagination-link[rel="next"]')
            new_page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
            if new_page > page:
                page = new_page

        return video_list

    def _extract_video_urls(self, bs4: BeautifulSoup, base_url: str, video_list: list):
        video_els = bs4.select('.movie-list .item a.box')
        for el in video_els:
            video_list.append(f'{base_url}{el["href"]}')


