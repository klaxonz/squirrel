import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common.http_wrapper import session
from meta.channel import SubscriptionMeta
from utils.cookie import filter_cookies_to_query_string
from ..base import BaseSubscription


class JavSubscription(BaseSubscription):
    DOMAIN = 'javdb.com'

    def get_subscribe_info(self):
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
        response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        bs4 = BeautifulSoup(response.text, 'html.parser')
        username_el = bs4.select('.actor-section-name')
        if len(username_el) == 0:
            raise Exception(f'Can not find channel name in {self.url}')

        name = username_el[0].text.strip()
        if ',' in name:
            name = name.split(',')[0]

        avatar_el = bs4.select('.avatar')[0]
        style = avatar_el['style']
        avatar = re.search(r'url\((.*?)\)', style).group(1)
        channel_id = self.url.split('/')[-1]

        return SubscriptionMeta(channel_id, name, avatar, self.url)

    def get_subscribe_videos(self, extract_all: bool):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }

        response = session.get(self.url, headers=headers, timeout=15)
        response.raise_for_status()

        parsed_url = urlparse(self.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        video_list = []
        
        bs4 = BeautifulSoup(response.text, 'html.parser')
        self._extract_video_urls(bs4, base_url, video_list)
        
        page_next_list = bs4.select('a.pagination-link[rel="next"]')
        page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
        current_page = 1

        while current_page < page and extract_all:
            current_page += 1
            response = session.get(self.url + f'?page={current_page}&sort_type=0&t=s', headers=headers, timeout=15)
            response.raise_for_status()
            bs4 = BeautifulSoup(response.text, 'html.parser')
            
            self._extract_video_urls(bs4, base_url, video_list)
            
            page_next_list = bs4.select('a.pagination-link[rel="next"]')
            new_page = int(bs4.select('a.pagination-link[rel="next"]')[0].text) if len(page_next_list) > 0 else 1
            if new_page > page:
                page = new_page

        return video_list

    def _extract_video_urls(self, bs4: BeautifulSoup, base_url: str, video_list: list):
        """Extract video URLs from BeautifulSoup object"""
        video_els = bs4.select('.movie-list .item a.box')
        for el in video_els:
            video_list.append(f'{base_url}{el["href"]}')
